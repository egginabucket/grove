from typing import Generator, Optional, Any

from maas.models import Lexeme
from language.models import SpacyLanguageModel
from carpet.base import (
    SHOW_BRACES, SHOW_PARANTHESES,
    MULTIPLIER_CHAR, COUNT_CHAR,
    Depth, Suffix, PitchChange,
)
from carpet.base import AbstractPhrase
from carpet.models import Phrase, Term, apply_model_phrase, parse_to_term_kwargs




"""
class _ModelPhrase(AbstractPhrase):
    true_attrs = ('phrase_obj', 'lang', 'has_braces')

    def __init__(self, lang: SpacyLanguageModel, phrase: Phrase):
        self = phrase
        self.phrase_obj = phrase
        self.lang = lang
"""

"""
class ModelPhrase(AbstractPhrase, Phrase):
    def __init__(self, lang: SpacyLanguageModel, phrase: Phrase):
        self = phrase
        self.__class__ = ModelPhrase
        self.lang = lang
        self.phrase_obj = phrase"""
    
"""
    @property
    def phrase_obj(self):
        phrase = self
        phrase.__class__ = Phrase
        #phrase.Meta.abstract = False
        return phrase
    """

"""
    def __getattr__(self, __name: str) -> Any:
        if __name in super().true_attrs:
            return getattr(self, __name)
        return getattr(self.phrase_obj, __name)
        
    def __setattr__(self, __name: str, __value: Any) -> None:
        if __name in super().true_attrs:
            return setattr(self, __name, __value)
        return setattr(self.phrase_obj, __name, __value)
    """
""" def get_children(self) -> Generator['Phrase', None, None]:
        for child_rel in self.phrase_obj.child_rels.order_by('index'):
            child = ModelPhrase(self.lang, child_rel.child)
            child.has_braces = child_rel.has_braces
            yield child
    
    def unwrapped_str(self) -> str:
        return str(self.lexeme) or ' '.join(map(str, self.get_children()))
    
    class Meta:
        abstract = True""" 
   


class StrPhrase(AbstractPhrase):
    lang_m: SpacyLanguageModel
    def __init__(self, lang_m: SpacyLanguageModel, phrase=''):
        self.lang_m = lang_m
        self.lang = lang_m.language
        self.phrase_str = phrase.strip()
        
    def get_children(self) -> Generator[AbstractPhrase, None, None]:   
        child = StrPhrase(self.lang_m)
        parentheses_depth = 0
        braces_depth = 0
        is_multiplier = False
        multiplier_str = ''
        is_count = False
        count_str = ''
        error_str = None
        is_term = True

        for i, char in enumerate(self.phrase_str + ' '):
            #if char not in TERM_CHARS and i < len(self.phrase_str):
            #    is_term = False
            maintain_term = False
            if char == '(':
                if parentheses_depth: child.phrase_str += char
                parentheses_depth += 1
            elif char == ')':
                parentheses_depth -= 1
                if parentheses_depth: child.phrase_str += char
                elif parentheses_depth < 0:
                    error_str = 'unopened ")"'
            elif char == '{':
                if braces_depth: child.phrase_str += char
                else: child.has_braces = True
                braces_depth += 1
                if parentheses_depth:
                    error_str = 'nested braces'
            elif char == '}':
                braces_depth -= 1
                if braces_depth: child.phrase_str += char
                elif braces_depth < 0:
                    error_str = 'unopened "}"'
            elif parentheses_depth or braces_depth:
                child.phrase_str += char
            
            elif not child.phrase_str and char in PitchChange.values:
                if child.pitch_change:
                    error_str = 'multiple tone changes'
                child.pitch_change = char
            elif char == MULTIPLIER_CHAR:
                is_multiplier = True
            elif is_multiplier and char.isdigit():
                multiplier_str += char
            elif char == COUNT_CHAR:
                is_count = True
            elif is_count and char.isdigit():
                count_str += char
            elif char in Suffix.values:
                if child.suffix:
                    error_str = 'multiple suffixes (use parentheses)'
                child.suffix = char
            elif char.isspace():
                if is_term:
                    try:
                        yield apply_model_phrase(self.lang, Term.objects.get(
                            **parse_to_term_kwargs(self.lang_m, child.phrase_str, True, False) # TODO
                        ).phrase)
                    except Term.DoesNotExist:
                        raise ValueError(f"undefined term '{child.phrase_str}'")
                else:
                    if multiplier_str:
                        child.multiplier *= int(multiplier_str)
                    if count_str:
                        if child.count is None:
                            child.count = 1
                        child.count *= int(count_str)
                    if len(child.phrase_str) > 0:
                        yield child
                child = StrPhrase(self.lang_m)
                parentheses_depth = 0
                braces_depth = 0
                is_multiplier = False
                multiplier_str = ''
                is_count = False
                count_str = ''
                is_term = True
            else:
                child.phrase_str += char
                maintain_term = True
                # error_str = 'unparsable token'
            if not maintain_term:
                is_term = False
            if error_str:
                raise ValueError(f"{error_str} at '{self.phrase_str}'[{i}]")
        if parentheses_depth:
            raise ValueError(f"unclosed parentheses in '{self.phrase_str}'")
        if braces_depth:
            raise ValueError(f"unclosed braces in '{self.phrase_str}'")
