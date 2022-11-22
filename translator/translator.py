from typing import Generator, Optional, Tuple, Iterable

from itertools import chain, islice
from django.conf import settings
from jangle.models import LanguageTag
from music21.note import Rest
from music21.stream.base import Score, Stream
from nltk.corpus import wordnet2021
from nltk.corpus.reader import (
    Synset,
    WordNetCorpusReader,
    WordNetICCorpusReader,
)
from spacy.glossary import GLOSSARY
from spacy.tokens import Token, Span

from nltk.corpus.reader import Synset
from maas.models import Lexeme
from carpet.base import AbstractPhrase, BasePhrase, Suffix
from carpet.stream import CarpetContext
from carpet.models import Phrase, SynsetDef
from translator.models import SpacyLanguage
from maas.utils import lexeme_from_en


ME = lexeme_from_en("me")
YOU = lexeme_from_en("you")
IT = lexeme_from_en("it")
PERSON = lexeme_from_en("person")
FEMALE = lexeme_from_en("girl")
MALE = lexeme_from_en("boy")


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
            similarity = synset.lin_similarity(related, ic)
            if similarity > largest_similarity:
                best = related
                largest_similarity = similarity
    return best


class TranslatorContext(CarpetContext):
    text_lang: LanguageTag
    wn: WordNetCorpusReader
    wn_ic: dict
    wn_lang: str
    peri_rest = Rest("whole")
    comm_rest = Rest("quarter")
    gender_pronouns = True
    max_l_grouping = 2
    max_r_grouping = 2
    hypernym_search_depth = 3
    hyponym_search_depth = 1
    _translated_tokens: set[Token] = set()
    _ent_phrases: dict[Span, AbstractPhrase] = dict()
    _skipped_tokens: list[Token] = []

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
    UP_DEPS = {}
    ENTITY_SKIP_DEPS = {
        "compound",
    }
    NUM_DEPS = {
        "nummod",
        "nmc",  # de
    }
    NEG_DEPS = {"neg", "ng"}  # de

    DEP_ORDERING = [
        "mark",
        "prep",
        "nsubj",
        "poss", # ?
        "aux",
        "det",
        "ROOT",
        "compound",
        "pcomp",
        "amod",
        "attr",
        "ag", #de
        "conj",
        "cj", #de
        "advmod",
        "advcl",
        "dative",
        "pobj",
        "dobj",
        "appos",
        "app", # de
        "dep",
    ]

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
        if token.pos_ == "PUNCT":
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
            if child in self._translated_tokens:
                continue
            phrase_token = True
            if phrase is not None and not child.children:
                phrase_token = False
                if child.dep_ == "neg":
                    phrase = BasePhrase([phrase], suffix=Suffix.NOT)
                elif child.pos_ == "PUNCT" and child.text == "?":
                    phrase = BasePhrase([phrase], suffix=Suffix.WHAT)
                elif child.dep_ == "nummod":
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
            if dep in self.UP_DEPS:
                self.phrase_up()
            elif dep not in self.NEUTRAL_DEPS:
                self.phrase_down()
            if dep == "ROOT":
                if phrase is not None:
                    stream.append(self.phrase_to_stream(phrase))
                elif root_m21_obj is not None:
                    stream.append(root_m21_obj)
            else:
                for token in child_phrase_tokens.get(dep, []):
                    stream.append(self.token_to_stream(token))
        return stream.flatten()

    def span_to_stream(self, span: Span) -> Stream:
        stream = Stream()
        self.reset_phrase()
        self._translated_tokens = set()
        self._ent_phrases = dict()

        for ent in span.ents:
            ent_lemma = text_to_wn_lemma(ent.label_)
            synsets = self.wn.synsets(ent_lemma, "n", self.wn_lang)
            if self.wn_lang != "eng" and not synsets:
                synsets = self.wn.synsets(ent_lemma, "n")
            related = find_related_defined_synset(
                synsets,
                self.wn_ic,
                self.hypernym_search_depth,
                self.hyponym_search_depth,
            )
            if related:
                self._ent_phrases[ent] = SynsetDef.objects.get_from_synset(
                    related
                ).phrase
            self._translated_tokens.update(iter(ent))
        for token in span:
            if token.dep_ == "ROOT":
                stream.append(self.token_to_stream(token))
                self.phrase_up()
        return stream
