from collections import defaultdict
from dataclasses import dataclass, field
from itertools import chain, islice
from typing import Generator, Optional, Tuple

from jangle.models import LanguageTag
from music21.note import Rest
from music21.spanner import Slur
from music21.stream.base import Score, Stream
from nltk.corpus.reader import Synset
from spacy import load
from spacy.language import Language
from spacy.tokens import Doc, Span, Token

from carpet.base import AbstractPhrase, BasePhrase, Suffix
from carpet.parser import StrPhrase
from carpet.models import SynsetDef
from carpet.speech import CarpetSpeech, PitchChange
from carpet.wordnet import wordnet
from maas.speech import MaasContext
from translator.misc_tokens import token_phrase
from translator.models import SpacyLanguage

SPECIAL_ENTS = {
    "DATE",
    "TIME",
    "PERCENT",
    "MONEY",
    "CARDINAL",
}  # TODO

ENT_FALLBACKS = {
    "PERSON": "person",
    "NORP": "[group] person",
    "ORG": "house",
    "LOC": "place",
    "GPE": "place",
    "PRODUCT": "thing",
    "EVENT": "@event.n.01",
    "LANGUAGE": "@language.n.01",
}

"""Fallback phrases for named entities if definitions cannot be found."""
DEP_ORDERING = [
    "mark",
    "intj",
    "nsubj",
    "csubj",
    "iobj",
    "possessive",
    "aux",
    "ROOT",
    "compound",
    "pcomp",
    "amod",
    "ag",  # de
    "rcmod",
    "relcl",
    "npadvmod",
    "advmod",
    "advcl",
    "acl",  # ?
    "dative",
    "part",
    "attr",  # ?
    "poss",  # ?
    "det",
    "pobj",
    "prep",
    "dobj",
    "obj",
    "acomp",
    "ccomp",
    "xcomp",
    "cc",
    "cd",  # de
    "conj",
    "cj",  # de
    "prt",  # ?
    "appos",
    "dep",
    # de
    "app",
    "mo",
    "app",
    "punct",
    "parataxis",
]
"""Ordering of a token's children in the final stream,
based on dependency relations.
Includes the token itself as 'ROOT'.
"""
NEUTRAL_DEPS = {
    "ROOT",
    "intj",
    "nsubj",
    "iobj",
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
    "poss",
    "det",
}
"""Dependency relations that don't denote a shift in the nucleus tone
(phrase_down is not called)"""
UP_DEPS = {"dobj", "pobj", "obj", "parataxis"}  # TODO: figure out auxiliaries
DOWN_ROOTS = {"ROOT", "relcl", "advcl", "acl"}
ALT_WORDNETS = {
    "ita": ["ita_iwn"],
}
WORDNET_POS = {
    "NOUN": "n",
    "PROPN": "n",
    "NUM": "n",
    "VERB": "v",
    "ADV": "r",
    "PART": "r",
    "ADJ": "a", # adds sat for en
}

_spacy_cache: dict[int, Language] = {}


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
    lefts = list(token.lefts)[-max_l:] if max_l else []
    rights = list(islice(token.rights, max_r))
    for l in range(len(lefts) + 1):
        for r in range(len(rights), -1, -1):
            tokens = [*lefts[l:], token, *rights[:r]]
            yield tokens


def related_synsets(
    synsets: list[tuple[Synset]],
    hypernym_search_depth: int,
    hyponym_search_depth: int,
    yielded=[],
) -> Generator[tuple[Synset], None, None]:
    """Navigates hypernyms & hyponyms recursively"""
    yield from synsets
    yielded.extend(s[0] for s in synsets)

    def related_chain(symbol: str) -> list[tuple]:
        return list(
            chain.from_iterable(
                (
                    (h, *s)
                    for h in s[0]._related(symbol, False)
                    if h not in yielded
                )
                for s in synsets
            )
        )

    if hypernym_search_depth > 0:
        yield from related_synsets(
            related_chain("@"),
            hypernym_search_depth - 1,
            hyponym_search_depth,
            yielded,
        )
    if hyponym_search_depth > 0:
        yield from related_synsets(
            related_chain("~"),
            hypernym_search_depth,
            hyponym_search_depth - 1,
            yielded,
        )


def _pron_carpet(token: Token, spec_gender=False) -> str:
    """only for fallback after misc_tokens.token_phrase"""
    if token.has_morph():
        person = token.morph.get("Person")
        if "3" in person:
            if spec_gender:
                if "Fem" in token.morph.get("Gender"):
                    return "girl"
                elif "Masc" in token.morph.get("Gender"):
                    return "boy"
            return "it"
        elif "1" in person:
            return "me"
        elif "2" in person:
            return "you"
    return "it"


@dataclass
class TranslatorContext(MaasContext):
    wn_lang: str = "eng"
    use_ner: bool = True
    show_det: bool = False
    sub_rel_ents: bool = False
    max_l_grouping: int = 2
    max_r_grouping: int = 2
    hypernym_search_depth: int = 6
    hyponym_search_depth: int = 2
    wn_ic: dict = field(default_factory=dict)


class Translation(CarpetSpeech):
    ctx: TranslatorContext

    token_history: dict[Token, list[str]]
    ent_phrases: dict[Span, AbstractPhrase]
    merged_tokens: dict[Token, Token]
    skipped_tokens: list[Token]

    def __init__(self, ctx: TranslatorContext, span: Span) -> None:
        super().__init__(ctx)
        self.span = span
        self.stream = Stream()
        self.token_history = {}
        self.skipped_tokens = []
        self.merged_tokens = {}
        self._first_det_used = False
        self.translate_ents()
        self.stream.append(self.token_to_stream(span.root))

    def score(self) -> Score:
        return self.ctx.build_score(self.span.text, self.stream)

    def token_used(self, token: Token) -> bool:
        if token in self.merged_tokens:
            return True
        if token in self.token_history:
            return True
        if token in self.skipped_tokens:
            return True
        return False

    def token_groups(self, token: Token) -> Generator[list[Token], None, None]:
        for tokens in token_groups(
            token, self.ctx.max_l_grouping, self.ctx.max_r_grouping
        ):
            do_yield = True
            for token in tokens:
                if self.token_used(token):
                    do_yield = False
                    break
            if do_yield:
                yield tokens

    def _synsets(
        self, lemma: str, pos: Optional[str], lang: str
    ) -> list[Synset]:
        synsets = wordnet.synsets(lemma, pos, lang)
        if lang != "eng" and pos == wordnet.ADJ:
            synsets += wordnet.synsets(lemma, wordnet.ADJ_SAT, lang)
        return synsets

    def synsets(self, lemma: str, pos: Optional[str] = None) -> list[Synset]:
        lemma = lemma.strip().replace(" ", "_")
        synsets = self._synsets(lemma, pos, self.ctx.wn_lang)
        for alt in ALT_WORDNETS.get(self.ctx.wn_lang, []):
            if synsets:
                break
            synsets = self._synsets(lemma, pos, alt)
        if self.ctx.wn_lang != "eng" and not synsets:
            synsets = self._synsets(lemma, pos, "eng")
        return synsets

    def potential_synset_lists(
        self, token: Token
    ) -> Generator[Tuple[list[Synset], list[Token]], None, None]:
        """Lists of directly matching synsets from various queries."""
        wn_pos = WORDNET_POS[token.pos_]
        token_texts = [
            (
                "".join(map(lambda t: t.text_with_ws, tokens)),
                tokens,
            )
            for tokens in self.token_groups(token)
        ]
        if token.lemma_ != token.text:
            token_texts.append((token.lemma_, [token]))
        if token.norm_ != token.text and token.norm_ != token.lemma_:
            token_texts.append((token.norm_, [token]))
        # wordnet uses morph substitutions
        for text, tokens in token_texts:
            yield self.synsets(text, wn_pos), tokens
            if len(tokens) > 1:
                # pos might not be accurate for groups of tokens
                yield self.synsets(text), tokens

    def token_to_phrase_via_wn(
        self, token: Token
    ) -> Tuple[Optional[AbstractPhrase], list[Token], tuple[Synset]]:
        for synsets, tokens in self.potential_synset_lists(token):
            related = related_synsets(
                list(zip(synsets)),
                self.ctx.hypernym_search_depth,
                self.ctx.hyponym_search_depth,
                [],
            )
            for synset in related:
                try:
                    def_ = SynsetDef.objects.get_from_synset(synset[0])
                    return def_.phrase, tokens, synset
                except SynsetDef.DoesNotExist:
                    pass
        return None, [], tuple()

    def modify_phrase(
        self, token: Token, phrase: AbstractPhrase
    ) -> Tuple[AbstractPhrase, bool]:
        modified = False
        if token.pos_ not in ("DET", "VERB"):
            if "Plur" in token.morph.get("Number"):
                if phrase.lexeme != StrPhrase("group").lexeme:
                    phrase.multiplier *= 2
                    modified = True
        if DEP_ORDERING.index("ROOT") < DEP_ORDERING.index(token.dep_):
            if token.has_head() and token.head in self.skipped_tokens:
                phrase, head_mod = self.modify_phrase(token.head, phrase)
                if head_mod:
                    self.skipped_tokens.remove(token.head)
                    modified = True
        for child in token.children:
            if self.token_used(child):
                continue
            merged = True
            if list(child.children):
                if child.dep_ in ("aux",):
                    phrase, aux_mod = self.modify_phrase(child, phrase)
                    if not aux_mod:
                        merged = False
                else:
                    merged = False
            else:
                if child.dep_ in ("neg", "ng"):
                    phrase = BasePhrase([phrase], suffix=Suffix.NOT)
                elif child.pos_ == "PUNCT" and child.text == "?":
                    phrase = BasePhrase([phrase], suffix=Suffix.WHAT)
                elif child.dep_ in ("nummod", "nmc"):
                    synsets_count = synsets_to_int(self.synsets(child.text))
                    if synsets_count is not None:
                        phrase.count = synsets_count
                else:
                    merged = False
            if merged:
                self.merged_tokens[child] = token
                modified = True
        return phrase, modified

    def token_to_stream(self, token: Token) -> Stream:
        is_skipped = False
        phrase = None
        root_m21_obj = None
        if self.token_used(token):
            pass
        elif token in chain.from_iterable(self.ent_phrases):
            for ent, ent_phrase in self.ent_phrases.items():
                if token in ent:
                    phrase = ent_phrase
                    self.token_history[token] = [
                        f"{ent.label_} (named entity)",
                    ]
                    for ent_t in ent:
                        self.merged_tokens[ent_t] = token
                    break
        elif token.pos_ == "PUNCT":
            if token.has_morph:
                punct_type = token.morph.get("PunctType")
                if "Peri" in punct_type:
                    root_m21_obj = Rest(self.ctx.peri_rest)
                elif "Comm" in punct_type:
                    root_m21_obj = Rest(self.ctx.comm_rest)
                else:
                    is_skipped = True
        elif token.pos_ == "DET":
            if self.ctx.show_det:
                if self._first_det_used:
                    phrase = StrPhrase("that")
                else:
                    phrase = StrPhrase("this")
                    self._first_det_used = True
            else:
                is_skipped = True
        elif token.pos_ == "PRON":
            if misc_phrase := token_phrase(token):
                phrase = misc_phrase
            else:
                carpet = _pron_carpet(token, self.ctx.gender_pronouns)
                phrase = StrPhrase(carpet)
        elif token.pos_ in WORDNET_POS:
            wn_phrase, merged, synsets = self.token_to_phrase_via_wn(token)
            if wn_phrase is not None:
                phrase = wn_phrase  # not necessary to wrap bc of how def strs are parsed
                self.token_history[token] = [
                    str(s.name()) for s in reversed(synsets)
                ]
                for merged_t in merged:
                    self.merged_tokens[merged_t] = token
            else:
                is_skipped = True
        elif misc_phrase := token_phrase(token):
            phrase = misc_phrase
        else:
            is_skipped = True
        if is_skipped:
            self.skipped_tokens.append(token)
        elif phrase is not None:
            if token in self.token_history:
                self.token_history[token].append(str(phrase))
            else:
                self.token_history[token] = [str(phrase)]
            phrase, modified = self.modify_phrase(token, phrase)
            if modified:
                self.token_history[token].append(str(phrase))
        child_phrase_tokens = defaultdict(list)
        for child in token.children:
            child_phrase_tokens[child.dep_].append(child)
        stream = Score()
        for dep in DEP_ORDERING:
            if dep == "ROOT":
                if phrase is not None:
                    if len(stream) and token.dep_ in DOWN_ROOTS:
                        phrase.pitch_change = PitchChange.DOWN
                    elif token.dep_ in UP_DEPS:
                        if token.has_head() and token.dep_ != "ROOT":
                            phrase.pitch_change = PitchChange.UP
                    elif token.dep_ not in NEUTRAL_DEPS:
                        phrase.pitch_change = PitchChange.DOWN
                    root_m21_obj = self.phrase_to_stream(phrase)
                if root_m21_obj is not None:
                    stream.append(root_m21_obj)
            else:
                for child in child_phrase_tokens[dep]:
                    stream.append(self.token_to_stream(child))
        return stream.flatten()

    def translate_ents(self) -> None:
        self.ent_phrases = {}
        if not self.ctx.use_ner:
            return
        for ent in self.span.ents:
            phrase = None
            synsets = list(zip(self.synsets(ent.text, wordnet.NOUN)))
            if self.ctx.sub_rel_ents:
                synsets = related_synsets(
                    synsets,
                    self.ctx.hypernym_search_depth,
                    self.ctx.hyponym_search_depth,
                    [],
                )
            for synset in synsets:
                try:
                    phrase = SynsetDef.objects.get_from_synset(
                        synset[0]
                    ).phrase
                    break
                except SynsetDef.DoesNotExist:
                    pass
            if not phrase and ent.label_ in ENT_FALLBACKS:
                phrase = StrPhrase(ENT_FALLBACKS[ent.label_])
            if phrase is not None:
                self.ent_phrases[ent] = phrase


# _ic = wordnet_ic.ic('ic-brown.dat')
def translate(
    ctx: TranslatorContext,
    text: str | Doc,
    lang: LanguageTag,
    add_lyrics=True,
) -> Tuple[Score, list[Translation]]:
    if not (lang.lang and lang.lang.iso_lang):
        raise ValueError(f"lang {lang} does not originate from ISO-639 3")
    ctx.wn_lang = lang.lang.iso_lang.part_3
    if add_lyrics:
        ctx.lyrics_lang = lang
    spacy_lang = SpacyLanguage.objects.from_lang(lang).largest()
    if spacy_lang is None:
        raise ValueError(f"no spacy models downloaded for {lang}")
    nlp = _spacy_cache.get(spacy_lang.pk)
    if nlp is None:
        nlp = load(spacy_lang.name)
        _spacy_cache[spacy_lang.pk] = nlp
    stream = Score()
    doc = nlp(text)
    speeches = []
    for sent in doc.sents:
        speech = Translation(ctx, sent)
        stream.append(speech.stream)
        speeches.append(speech)
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
    return ctx.build_score(str(doc), stream), speeches
