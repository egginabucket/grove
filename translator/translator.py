from itertools import chain, islice
from typing import Generator, Iterable, Optional, Tuple

from django.conf import settings
from jangle.models import LanguageTag
from music21.note import Rest
from music21.spanner import Slur
from music21.stream.base import Score, Stream
from nltk.corpus import wordnet2021, wordnet_ic
from nltk.corpus.reader import Synset, WordNetCorpusReader
from spacy import load
from spacy.glossary import GLOSSARY
from spacy.language import Language
from spacy.tokens import Span, Token

from carpet.base import AbstractPhrase, BasePhrase, Suffix
from carpet.models import SynsetDef
from carpet.stream import CarpetContext
from maas.utils import EN, lexeme_from_en
from translator.models import SpacyLanguage

ME = lexeme_from_en("me")
YOU = lexeme_from_en("you")
IT = lexeme_from_en("it")
PERSON = lexeme_from_en("person")
FEMALE = lexeme_from_en("girl")
MALE = lexeme_from_en("boy")
GROUP = lexeme_from_en("group")
HOUSE = lexeme_from_en("house")
PLACE = lexeme_from_en("place")
TALK = lexeme_from_en("talk")
THING = lexeme_from_en("thing")
TIME = lexeme_from_en("time")


_spacy_cache: dict[str, Language] = {}


def text_to_wn_lemma(text: str) -> str:
    return text.strip().replace(" ", "_")


def synsets_to_int(synsets: list[Synset]) -> Optional[int]:
    """Eg takes synsets for "twelve" and returns 12."""
    for synset in synsets:
        for name in synset.lemma_names():
            try:
                return int(name)
            except ValueError:
                pass


def token_groups(
    token: Token, max_l: int, max_r: int
) -> Generator[list[Token], None, None]:
    lefts = list(token.lefts)[-max_l:]
    rights = list(islice(token.rights, max_r))
    for l in range(len(lefts) + 1):
        for r in reversed(range(len(rights) + 1)):
            tokens = [*lefts[l:], token, *rights[:r]]
            yield tokens


def related_synsets(
    synset: Synset,
    hypernym_search_depth: int,
    hyponym_search_depth: int,
) -> Generator[Synset, None, None]:
    """Navigates hypernyms & hyponyms recursively"""
    yield synset
    if hypernym_search_depth > 0:
        for hypernym in synset.hypernyms():
            yield from related_synsets(
                hypernym,
                hypernym_search_depth,
                hyponym_search_depth - 1,
            )
    if hyponym_search_depth > 0:
        for hyponym in synset.hyponyms():
            yield from related_synsets(
                hyponym,
                hypernym_search_depth - 1,
                hyponym_search_depth,
            )


def find_related_defined_synset(
    synsets: Iterable[Synset],
    ic: dict,
    hypernym_search_depth=3,
    hyponym_search_depth=1,
) -> Optional[Synset]:
    best = None
    largest_similarity = 0.0
    for synset in synsets:
        for related in related_synsets(
            synset, hypernym_search_depth, hyponym_search_depth
        ):
            if not SynsetDef.objects.from_synset(related).exists():
                continue
            #similarity = synset.lin_similarity(related, ic)
            similarity = synset.path_similarity(related) or 0.0
            if similarity > largest_similarity:
                best = related
                largest_similarity = similarity
    return best


class TranslatorContext(CarpetContext):
    text_lang: LanguageTag
    wn: WordNetCorpusReader
    wn_ic: dict
    wn_lang: str
    sub_rel_ents = False
    gender_pronouns = True
    peri_rest = Rest("whole")
    comm_rest = Rest("quarter")
    max_l_grouping = 2
    max_r_grouping = 2
    hypernym_search_depth = 3
    hyponym_search_depth = 1
    _translated_tokens: set[Token] = set()
    _ent_phrases: dict[Span, AbstractPhrase] = {}
    _skipped_tokens: list[Token] = []

    SPECIAL_ENTS = {
        "DATE",
        "TIME",
        "PERCENT",
        "MONEY",
        "CARDINAL",
    }  # TODO
    ENT_FALLBACKS = {
        "PERSON": BasePhrase(lexeme=PERSON),
        "NORP": BasePhrase(
            [BasePhrase(lexeme=GROUP), BasePhrase(lexeme=PERSON)]
        ),
        "ORG": BasePhrase(lexeme=HOUSE),
        "LOC": BasePhrase(lexeme=PLACE),
        "GPE": BasePhrase(lexeme=PLACE),
        "PRODUCT": BasePhrase(lexeme=THING),
        "EVENT": BasePhrase(
            [BasePhrase(lexeme=THING), BasePhrase(lexeme=TIME)]
        ),
        "LANGUAGE": BasePhrase(
            [BasePhrase(lexeme=TALK), BasePhrase(lexeme=HOUSE)]
        ),
    }
    """Fallback phrases for named entities if definitions cannot be found."""
    DEP_ORDERING = [
        "mark",
        "prep",
        "nsubj",
        "possessive",
        "poss",  # ?
        "aux",
        "det",
        "ROOT",
        "compound",
        "pcomp",
        "amod",
        "attr",
        "ag",  # de
        "conj",
        "cj",  # de
        "advmod",
        "advcl",
        "dative",
        "pobj",
        "dobj",
        "appos",
        "app",  # de
        "dep",
        #de
        "mo",
        "ag",
        "cj",
        "app",
        "punct",
    ]
    """Ordering of a token's children in the final stream,
    based on dependency relations.
    Includes the token itself as 'ROOT'.
    """
    NEUTRAL_DEPS = {
        "case",
        "acl",
        "npadvmod",
        "advmod",
        "amod",
        "prep",
        "mo",
        "neg",
        "nummod",
        "ng",
        "nmc",
    }
    """Dependency relations that don't denote a shift in the nucleus tone
    (phrase_up is not called)"""
    UP_DEPS = set() # TODO: remove
    NEG_DEPS = {"neg", "ng"}  # de

    def token_groups(self, token: Token) -> Generator[list[Token], None, None]:
        for tokens in token_groups(
            token, self.max_l_grouping, self.max_r_grouping
        ):
            for token in tokens:
                if token in self._translated_tokens:
                    continue
            yield tokens

    def potential_synset_lists(
        self, token: Token
    ) -> Generator[Tuple[list[Synset], list[Token]], None, None]:
        """Lists of directly matching synsets from various queries."""
        wn_pos = None
        if token.pos_ in {"NOUN", "PROPN"}:
            wn_pos = self.wn.NOUN
        elif token.pos_ == "VERB":
            wn_pos = self.wn.VERB
        elif token.pos_ == "ADJ":
            wn_pos = self.wn.ADJ  # wn also finds satellites
        elif token.pos_ == "ADV":
            wn_pos = self.wn.ADV
        token_texts = [
            (
                text_to_wn_lemma(
                    "".join(map(lambda t: t.text_with_ws, tokens))
                ),
                tokens,
            )
            for tokens in self.token_groups(token)
        ]
        if token.lemma_ != token.text:
            token_texts.append((token.lemma_, [token]))
        # wordnet uses morph substitutions
        for text, tokens in token_texts:
            for q_token in tokens:
                if q_token in self._translated_tokens:
                    continue
            yield self.wn.synsets(text, wn_pos, self.wn_lang), tokens
            if self.wn_lang != "eng":
                yield self.wn.synsets(text, wn_pos), tokens
            yield self.wn.synsets(text, lang=self.wn_lang), tokens
            if self.wn_lang != "eng":
                yield self.wn.synsets(text), tokens

    def token_to_phrase_via_wn(
        self, token: Token
    ) -> Tuple[Optional[AbstractPhrase], list[Token]]:
        for synsets, tokens in self.potential_synset_lists(token):
            for synset in synsets:
                try:
                    def_ = SynsetDef.objects.get_from_synset(synset)
                    return def_.phrase, tokens
                except SynsetDef.DoesNotExist:
                    pass
        for synsets, tokens in self.potential_synset_lists(token):
            related = find_related_defined_synset(
                synsets,
                self.wn_ic,
                self.hypernym_search_depth,
                self.hyponym_search_depth,
            )
            if related:
                try:
                    def_ = SynsetDef.objects.get_from_synset(related)
                    return def_.phrase, tokens
                except SynsetDef.DoesNotExist:
                    pass
        return None, []

    def token_to_stream(self, token: Token) -> Stream:
        is_skipped = False
        phrase = None
        root_m21_obj = None
        if token in self._translated_tokens:
            pass
        elif token in chain(*self._ent_phrases):
            for ent, ent_phrase in self._ent_phrases.items():
                if token in ent:
                    phrase = ent_phrase
                    self._translated_tokens.update(iter(ent))
                    break
        elif token.pos_ == "PUNCT":
            if token.has_morph:
                punct_type = token.morph.get("PunctType")
                if punct_type == ["Peri"]:
                    # if token.text == '?': pass
                    root_m21_obj = self.peri_rest
                elif punct_type == ["Comm"]:
                    root_m21_obj = self.comm_rest
                else:
                    is_skipped = True
        elif token.pos_ == "PRON":
            is_personal = "Prs" in token.morph.get("PronType")
            person = token.morph.get("Person")
            if "3" in person:
                phrase = BasePhrase(lexeme=IT)
                if is_personal:
                    phrase = BasePhrase([phrase, BasePhrase(lexeme=PERSON)])
                    if self.gender_pronouns:
                        if "Fem" in token.morph.get("Gender"):
                            phrase.children.append(BasePhrase(lexeme=FEMALE))
                        elif "Masc" in token.morph.get("Gender"):
                            phrase.children.append(BasePhrase(lexeme=MALE))
            elif "1" in person:
                if is_personal:
                    phrase = BasePhrase(lexeme=ME)
                else:
                    is_skipped = True
            elif "2" in person:
                if is_personal:
                    phrase = BasePhrase(lexeme=YOU)
                else:
                    is_skipped = True
            else:
                is_skipped = True
            self._translated_tokens.add(token)
        elif token.pos_ in {"NOUN", "PROPN", "VERB", "ADJ", "ADV"}:
            wn_phrase, tokens = self.token_to_phrase_via_wn(token)
            if wn_phrase is not None:
                phrase = wn_phrase
                self._translated_tokens.update(tokens)
            else:
                is_skipped = True
        else:
            is_skipped = True
        if "Plur" in token.morph.get("Number"):
            if phrase is not None:
                phrase.multiplier *= 2
        if is_skipped:
            self._skipped_tokens.append(token)
        else:
            self._translated_tokens.add(token)
        child_phrase_tokens: dict[str, list[Token]] = {}
        for child in token.children:
            phrase_token = True
            if (
                phrase is not None
                and child not in self._translated_tokens
                and not list(child.children)
            ):
                phrase_token = False
                if child.dep_ in {"neg", "ng"}:
                    phrase = BasePhrase([phrase], suffix=Suffix.NOT)
                elif child.pos_ == "PUNCT" and child.text == "?":
                    phrase = BasePhrase([phrase], suffix=Suffix.WHAT)
                elif child.dep_ in {"nummod", "nmc"}:
                    try:
                        count = synsets_to_int(self.wn.synsets(child.text))
                    except ValueError:
                        count = None  # TODO: let user change?
                    phrase = BasePhrase([phrase], count=count)
                else:
                    phrase_token = True
            if phrase_token:
                if child.dep_ in child_phrase_tokens:
                    child_phrase_tokens[child.dep_].append(child)
                else:
                    child_phrase_tokens[child.dep_] = [child]

        stream = Score()
        for dep in self.DEP_ORDERING:
            if dep == "ROOT":
                if phrase is not None:
                    stream.append(self.phrase_to_stream(phrase))
                elif root_m21_obj is not None:
                    stream.append(root_m21_obj)
            else:
                for token in child_phrase_tokens.get(dep, []):
                    if dep in self.UP_DEPS:
                        self.phrase_up()
                    elif dep not in self.NEUTRAL_DEPS:
                        self.phrase_down()
                    stream.append(self.token_to_stream(token))
        return stream.flatten()

    def span_to_stream(self, span: Span) -> Stream:
        stream = Stream()
        self.reset_phrase()
        self._translated_tokens = set()
        self._skipped_tokens = []
        self._ent_phrases = {}

        for ent in span.ents:
            ent_lemma = text_to_wn_lemma(ent.text)
            synsets = self.wn.synsets(ent_lemma, self.wn.NOUN, self.wn_lang)
            if self.wn_lang != "eng" and not synsets:
                synsets = self.wn.synsets(ent_lemma, self.wn.NOUN)
            phrase = None
            for synset in synsets:
                try:
                    phrase = SynsetDef.objects.get_from_synset(synset).phrase
                except SynsetDef.DoesNotExist:
                    pass
            if phrase is None and self.sub_rel_ents:
                related = find_related_defined_synset(
                    synsets,
                    self.wn_ic,
                    self.hypernym_search_depth,
                    self.hyponym_search_depth,
                )
                if related is not None:
                    phrase = SynsetDef.objects.get_from_synset(related).phrase
            if not phrase and ent.label_ in self.ENT_FALLBACKS:
                phrase = self.ENT_FALLBACKS[ent.label_]
            if phrase is not None:
                self._ent_phrases[ent] = phrase
        for token in span:
            if token.dep_ == "ROOT":
                stream.append(self.token_to_stream(token))
                self.phrase_up()
        return stream.flatten()

_ic = wordnet_ic.ic('ic-brown.dat')
def translate(text: str, lang=EN, add_lyrics=True, *args, **kwargs) -> Score:
    if not (lang.lang and lang.lang.iso_lang):
        raise ValueError(f"lang {lang} does not originate from ISO-639 3")
    ctx = TranslatorContext(*args, **kwargs)
    if add_lyrics:
        ctx.lyrics_lang = lang
    wordnet2021.ensure_loaded()
    ctx.wn = wordnet2021 # type: ignore
    ctx.wn_ic = _ic
    ctx.wn_lang = lang.lang.iso_lang.part_3
    spacy_lang = SpacyLanguage.objects.from_lang(lang).largest()
    if spacy_lang is None:
        raise ValueError(f"no spacy models downloaded for {lang}")
    nlp = _spacy_cache.get(spacy_lang.name)
    if nlp is None:
        nlp = load(spacy_lang.name)
        _spacy_cache[spacy_lang.name] = nlp
    stream = Score()
    doc = nlp(text)
    for sent in doc.sents:
        stream.append(ctx.span_to_stream(sent))
        print("Skipped tokens:", ctx._skipped_tokens)
        print("Entities:", ctx._ent_phrases)
    stream = stream.flatten()
    last = stream.last()
    if isinstance(last, Rest) and len(last.lyrics) == 0:
        for spanner in last.getSpannerSites():
            if isinstance(spanner, Slur):
                continue
        stream.pop(len(stream) - 1)
    return ctx.build_score(str(doc), stream)