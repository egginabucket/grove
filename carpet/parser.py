from typing import Any, Generator, Optional

from jangle.models import LanguageTag

from carpet.base import (
    CLOSE_CHAR,
    COUNT_CHAR,
    MULTIPLIER_CHAR,
    OPEN_CHAR,
    PRIMARY_CLOSE_CHAR,
    PRIMARY_OPEN_CHAR,
    SYNSET_CHAR,
    AbstractPhrase,
    PitchChange,
    Suffix,
)
from carpet.models import Phrase, PhraseComposition, SynsetDef
from carpet.wordnet import wordnet
from maas.models import LexemeTranslation, NativeLang


class StrPhrase(AbstractPhrase):
    lang: LanguageTag
    phrase_str: str = ""
    is_synset_linked = False

    def _check_lexeme(self):
        if self.phrase_str.isalpha():
            try:
                self.lexeme = LexemeTranslation.objects.get(
                    word=self.phrase_str,
                    lang=self.lang,
                ).lexeme
                self.phrase_str = ""
            except LexemeTranslation.DoesNotExist as e:
                raise LexemeTranslation.DoesNotExist(
                    f"lexeme '{self.phrase_str}'"
                ) from e

    def __init__(self, phrase: str, lang=NativeLang()) -> None:
        self.lang = lang
        self.phrase_str = phrase.strip()
        if self.phrase_str:
            self._check_lexeme()

    def _get_children(self) -> Generator[AbstractPhrase, None, None]:
        if self.lexeme is not None:
            return
        if self.is_synset_linked:
            try:
                synset = wordnet.synset(self.phrase_str)
                yield SynsetDef.objects.get_from_synset(synset).phrase # type: ignore
            except SynsetDef.DoesNotExist as e:
                raise SynsetDef.DoesNotExist(
                    f"undefined synset '{self.phrase_str}'"
                ) from e
            return
        child = StrPhrase("", self.lang)
        depth = 0
        primary_depth = 0
        is_multiplier = False
        multiplier_str = ""
        is_count = False
        count_str = ""
        error_str = None

        for i, char in enumerate(self.phrase_str + " "):
            if char == OPEN_CHAR:
                if depth:
                    child.phrase_str += char
                depth += 1
            elif char == CLOSE_CHAR:
                depth -= 1
                if depth:
                    child.phrase_str += char
                elif depth < 0:
                    error_str = f"unopened '{CLOSE_CHAR}'"
            elif char == PRIMARY_OPEN_CHAR:
                if primary_depth:
                    child.phrase_str += char
                else:
                    child.is_primary = True
                primary_depth += 1
                if depth:
                    error_str = "nested primary subphrase"
            elif char == PRIMARY_CLOSE_CHAR:
                primary_depth -= 1
                if primary_depth:
                    child.phrase_str += char
                elif primary_depth < 0:
                    error_str = "unopened '{PRIMARY_CLOSE_CHAR}'"
            elif primary_depth or primary_depth:
                child.phrase_str += char
            elif not child.phrase_str and char in PitchChange.values:
                if child.pitch_change:
                    error_str = "multiple tone changes"
                child.pitch_change = char
            elif not child.phrase_str and char == SYNSET_CHAR:
                if child.is_synset_linked:
                    error_str = f"repeated '{SYNSET_CHAR}'"
                child.is_synset_linked = True
            elif char == MULTIPLIER_CHAR:
                if is_multiplier:
                    error_str = f"repeated '{MULTIPLIER_CHAR}'"
                is_multiplier = True
            elif is_multiplier and char.isdigit():
                multiplier_str += char
            elif char == COUNT_CHAR:
                if is_count:
                    error_str = f"repeated '{COUNT_CHAR}'"
                is_count = True
            elif is_count and char.isdigit():
                count_str += char
            elif char in Suffix.values:
                if child.suffix:
                    error_str = "multiple suffixes (use parentheses)"
                child.suffix = char
            elif char.isspace():
                child.phrase_str = child.phrase_str.strip()
                if child.phrase_str:
                    if multiplier_str:
                        child.multiplier *= int(multiplier_str)
                    if count_str:
                        if child.count is None:
                            child.count = 1
                        child.count *= int(count_str)
                    child._check_lexeme()
                    yield child
                child = StrPhrase("", self.lang)
                depth = 0
                primary_depth = 0
                is_multiplier = False
                multiplier_str = ""
                is_count = False
                count_str = ""
            else:
                child.phrase_str += char
            if error_str:
                raise ValueError(f"{error_str} at '{self.phrase_str}'[{i}]")
        if depth:
            raise ValueError(f"unclosed '{OPEN_CHAR}' in '{self.phrase_str}'")
        if primary_depth:
            raise ValueError(
                f"unclosed '{PRIMARY_CLOSE_CHAR}' in '{self.phrase_str}'"
            )

    def save(self) -> Phrase:
        obj = Phrase.objects.create(
            pitch_change=self.pitch_change,
            multiplier=self.multiplier,
            suffix=self.suffix,
            count=self.count,
            lexeme=self.lexeme,
        )
        for i, child in enumerate(self.children):
            if isinstance(child, self.__class__):
                child_obj = child.save()
            else:
                child_obj = child
            PhraseComposition.objects.create(
                parent=obj,
                child=child_obj,
                index=i,
                is_primary=child.is_primary,
            )
        return obj
