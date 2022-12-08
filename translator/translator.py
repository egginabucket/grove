from dataclasses import dataclass, field
from itertools import chain, islice
from typing import Generator, Iterable, Optional, Tuple

from music21.note import Rest
from music21.spanner import Slur
from music21.stream.base import Score, Stream
from nltk.corpus.reader import Synset
from spacy import load
from spacy.glossary import GLOSSARY
from spacy.language import Language
from spacy.tokens import Doc, Span, Token

from carpet.base import AbstractPhrase, BasePhrase, Suffix
from carpet.models import SynsetDef
from carpet.speech import CarpetSpeech
from carpet.wordnet import wordnet
from maas.music import MaasContext
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
THIS = lexeme_from_en("this")
THAT = lexeme_from_en("that")
AND = lexeme_from_en("and")


SPECIAL_ENTS = {
    "DATE",
    "TIME",
    "PERCENT",
    "MONEY",
    "CARDINAL",
}  # TODO
ENT_FALLBACKS = {
    "PERSON": BasePhrase(lexeme=PERSON),
    "NORP": BasePhrase([BasePhrase(lexeme=GROUP), BasePhrase(lexeme=PERSON)]),
    "ORG": BasePhrase(lexeme=HOUSE),
    "LOC": BasePhrase(lexeme=PLACE),
    "GPE": BasePhrase(lexeme=PLACE),
    "PRODUCT": BasePhrase(lexeme=THING),
    "EVENT": BasePhrase([BasePhrase(lexeme=THING), BasePhrase(lexeme=TIME)]),
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
    "ag",  # de
    "cc",
    "cd", # de
    "conj",
    "cj",  # de
    "rcmod",
    "relcl",
    "advmod",
    "advcl",
    "dative",
    "part",
    "attr",  # ?
    "pobj",
    "dobj",
    "acomp",
    "ccomp",
    "xcomp",
    "appos",
    "dep",
    # de
    "app",
    "mo",
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
    "det",
}
"""Dependency relations that don't denote a shift in the nucleus tone
(phrase_up is not called)"""
UP_DEPS = {"aux", "nsubj"}  # TODO: figure out auxiliaries
NEG_DEPS = {"neg", "ng"}  # de
ALT_WORDNETS = {
    "ita": ["ita_iwn"],
}

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
    cur_depth=0,
) -> Generator[Tuple[Synset, int], None, None]:
    """Navigates hypernyms & hyponyms recursively"""
    yield synset, cur_depth
    cur_depth += 1
    if hypernym_search_depth > 0:
        for hypernym in synset.hypernyms():
            yield from related_synsets(
                hypernym,
                hypernym_search_depth - 1,
                hyponym_search_depth,
                cur_depth,
            )
    if hyponym_search_depth > 0:
        for hyponym in synset.hyponyms():
            yield from related_synsets(
                hyponym,
                hypernym_search_depth,
                hyponym_search_depth - 1,
                cur_depth,
            )


def find_related_defined_synset(
    synsets: Iterable[Synset],
    ic: dict,
    hypernym_search_depth=3,
    hyponym_search_depth=1,
) -> Optional[Synset]:
    best = None
    lowest_depth = -1
    for synset in synsets:
        for related, depth in related_synsets(
            synset, hypernym_search_depth, hyponym_search_depth
        ):
            # similarity = synset.lin_similarity(related, ic)
            # similarity = synset.path_similarity(related) or 0.0
            if (
                (lowest_depth == -1 or depth < lowest_depth)
                and (best is None or best != related)
                and SynsetDef.objects.from_synset(related).exists()
            ):
                best = related
                lowest_depth = depth
    return best


@dataclass
class TranslatorContext(MaasContext):
    wn_lang = "eng"
    sub_rel_ents: bool = False
    max_l_grouping: int = 2
    max_r_grouping: int = 2
    hypernym_search_depth: int = 4
    hyponym_search_depth: int = 2
    wn_ic: dict = field(default_factory=dict)


class Translation(CarpetSpeech):
    ctx: TranslatorContext
    span: Span
    stream: Stream

    translated_tokens: set[Token]
    ent_phrases: dict[Span, AbstractPhrase]
    skipped_tokens: list[Token]
    _first_det_used = False

    def __init__(self, ctx: TranslatorContext, span: Span) -> None:
        super().__init__(ctx)
        self.span = span
        self.stream = Stream()
        self.translated_tokens = set()
        self.ent_phrases = {}
        self.skipped_tokens = []
        self.translate_ents()
        for token in span:
            if token.dep_ == "ROOT":
                self.stream.append(self.token_to_stream(token))
                self.phrase_up()

    def score(self) -> Score:
        return self.ctx.build_score(self.span.text, self.stream)

    def token_groups(self, token: Token) -> Generator[list[Token], None, None]:
        for tokens in token_groups(
            token, self.ctx.max_l_grouping, self.ctx.max_r_grouping
        ):
            for token in tokens:
                if token in self.translated_tokens:
                    continue
            yield tokens

    def synsets(self, lemma: str, pos: Optional[str] = None) -> list[Synset]:
        synsets = wordnet.synsets(lemma, pos, self.ctx.wn_lang)
        for alt in ALT_WORDNETS.get(self.ctx.wn_lang, []):
            if synsets:
                break
            synsets = wordnet.synsets(lemma, pos, alt)
        if self.ctx.wn_lang != "eng" and not synsets:
            synsets = wordnet.synsets(lemma, pos, "eng")
        return synsets

    def potential_synset_lists(
        self, token: Token
    ) -> Generator[Tuple[list[Synset], list[Token]], None, None]:
        """Lists of directly matching synsets from various queries."""
        wn_pos = None
        if token.pos_ in {"NOUN", "PROPN", "NUM"}:
            wn_pos = wordnet.NOUN
        elif token.pos_ == "VERB":
            wn_pos = wordnet.VERB
        elif token.pos_ == "ADJ":
            wn_pos = wordnet.ADJ  # wn also finds satellites
        elif token.pos in {"ADV", "PART"}:
            wn_pos = wordnet.ADV
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
                if q_token in self.translated_tokens:
                    continue
            yield self.synsets(text, wn_pos), tokens
            if len(tokens) > 1:
                # pos might not be accurate for groups of tokens
                yield self.synsets(text), tokens

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
                self.ctx.wn_ic,
                self.ctx.hypernym_search_depth,
                self.ctx.hyponym_search_depth,
            )
            if related is not None:
                return (
                    SynsetDef.objects.get_from_synset(related).phrase,
                    tokens,
                )
        return None, []

    def token_to_stream(self, token: Token) -> Stream:
        is_skipped = False
        phrase = None
        root_m21_obj = None
        if token in self.translated_tokens:
            pass
        elif token in chain(*self.ent_phrases):
            for ent, ent_phrase in self.ent_phrases.items():
                if token in ent:
                    phrase = ent_phrase
                    self.translated_tokens.update(iter(ent))
                    break
        elif token.pos_ == "PUNCT":
            if token.has_morph:
                punct_type = token.morph.get("PunctType")
                if punct_type == ["Peri"]:
                    root_m21_obj = Rest(self.ctx.peri_rest)
                elif punct_type == ["Comm"]:
                    root_m21_obj = Rest(self.ctx.comm_rest)
                else:
                    is_skipped = True
        elif token.pos_ == "DET":
            if self._first_det_used:
                phrase = BasePhrase(lexeme=THAT)
            else:
                phrase = BasePhrase(lexeme=THIS)
                self._first_det_used = True
        elif token.pos_ == "PRON":
            is_personal = "Prs" in token.morph.get("PronType")
            person = token.morph.get("Person")
            if "3" in person:
                phrase = BasePhrase(lexeme=IT)
                if is_personal:
                    phrase = BasePhrase([phrase, BasePhrase(lexeme=PERSON)])
                    if self.ctx.gender_pronouns:
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
            self.translated_tokens.add(token)
        elif token.pos_ == "CCONJ":
            if "Cmp" in token.morph.get("ConjType"):
                phrase = BasePhrase(lexeme=AND)
        elif token.pos_ in {
            "NOUN",
            "PROPN",
            "NUM",
            "VERB",
            "ADJ",
            "ADV",
            "PART",
        }:
            wn_phrase, tokens = self.token_to_phrase_via_wn(token)
            if wn_phrase is not None:
                phrase = wn_phrase
                self.translated_tokens.update(tokens)
            else:
                is_skipped = True
        else:
            is_skipped = True
        if "Plur" in token.morph.get("Number"):
            if phrase is not None:
                phrase.multiplier *= 2
        if is_skipped:
            self.skipped_tokens.append(token)
        else:
            self.translated_tokens.add(token)
        child_phrase_tokens: dict[str, list[Token]] = {}
        for child in token.children:
            phrase_token = True
            if (
                phrase is not None
                and child not in self.translated_tokens
                and not list(child.children)
            ):
                phrase_token = False
                if child.dep_ in {"neg", "ng"}:
                    phrase = BasePhrase([phrase], suffix=Suffix.NOT)
                elif child.pos_ == "PUNCT" and child.text == "?":
                    phrase = BasePhrase([phrase], suffix=Suffix.WHAT)
                elif child.dep_ in {"nummod", "nmc"}:
                    try:
                        count = synsets_to_int(self.synsets(child.text))
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
        for dep in DEP_ORDERING:
            if dep == "ROOT":
                if phrase is not None:
                    stream.append(self.phrase_to_stream(phrase))
                elif root_m21_obj is not None:
                    stream.append(root_m21_obj)
            else:
                for token in child_phrase_tokens.get(dep, []):
                    if dep in UP_DEPS:
                        self.phrase_up()
                    elif dep not in NEUTRAL_DEPS:
                        self.phrase_down()
                    stream.append(self.token_to_stream(token))
        return stream.flatten()

    def translate_ents(self) -> None:
        for ent in self.span.ents:
            ent_lemma = text_to_wn_lemma(ent.text)
            synsets = self.synsets(ent_lemma, wordnet.NOUN)
            phrase = None
            for synset in synsets:
                try:
                    phrase = SynsetDef.objects.get_from_synset(synset).phrase
                except SynsetDef.DoesNotExist:
                    pass
            if phrase is None and self.ctx.sub_rel_ents:
                related = find_related_defined_synset(
                    synsets,
                    self.ctx.wn_ic,
                    self.ctx.hypernym_search_depth,
                    self.ctx.hyponym_search_depth,
                )
                if related is not None:
                    phrase = SynsetDef.objects.get_from_synset(related).phrase
            if not phrase and ent.label_ in ENT_FALLBACKS:
                phrase = ENT_FALLBACKS[ent.label_]
            if phrase is not None:
                self.ent_phrases[ent] = phrase


# _ic = wordnet_ic.ic('ic-brown.dat')
def translate(
    ctx: TranslatorContext,
    text: str | Doc,
    lang=EN,
    add_lyrics=True,
) -> Score:
    if not (lang.lang and lang.lang.iso_lang):
        raise ValueError(f"lang {lang} does not originate from ISO-639 3")
    ctx.wn_lang = lang.lang.iso_lang.part_3
    if add_lyrics:
        ctx.lyrics_lang = lang
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
        speech = Translation(ctx, sent)
        stream.append(speech.stream)
        print("Skipped tokens:", speech.skipped_tokens)
        print("Entities:", speech.ent_phrases)
    stream = stream.flatten()
    last = stream.last()
    if isinstance(last, Rest) and len(last.lyrics) == 0:
        has_slur = False
        for spanner in last.getSpannerSites():
            if isinstance(spanner, Slur):
                has_slur = True
                break
        if not has_slur:
            stream.pop(len(stream) - 1)
    return ctx.build_score(str(doc), stream)
