from typing import Optional
from maas.models import Lexeme
from carpet import models
from carpet.common import *

class StrPhrase(AbstractPhrase):
    has_braces = False
    tone_change = None
    suffix = ''
    multiplier = 1
    count: Optional[int] = None

    def __init__(self, phrase='', *args, **kwargs):
        self.phrase_str = phrase.strip()
    
    def get_children(self) -> Generator[AbstractPhrase]:   
        child = StrPhrase()
        parentheses_depth = 0
        braces_depth = 0
        is_multiplier = False
        multiplier_str = ''
        is_count = False
        count_str = ''
        error_str = None
        is_term = True

        for i, char in enumerate(self.phrase_str + ' '):
            if char not in TERM_CHARS:
                is_term = False
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
            
            elif not child.phrase_str and char in models.Phrase.ToneChange.values:
                if child.tone_change:
                    error_str = 'multiple tone changes'
                child.tone_change = char
            elif char in TERM_CHARS:
                child.phrase_str += char
            elif char == MULTIPLIER_CHAR:
                is_multiplier = True
            elif is_multiplier and char.isdigit():
                multiplier_str += char
            elif char == COUNT_CHAR:
                is_count = True
            elif is_count and char.isdigit():
                count_str += char
            elif char in models.Phrase.Suffix.values:
                if child.suffix:
                    error_str = 'multiple suffixes (use parentheses)'
                child.suffix = char
            elif char.isspace():
                if is_term:
                    self.children.append()
                else:
                    if multiplier_str:
                        child.multiplier *= int(multiplier_str)
                    if count_str:
                        if child.count is None:
                            child.count = 1
                        child.count *= int(count_str)
                    if len(child.phrase_str) > 0:
                        yield child
                child = StrPhrase()
                parentheses_depth = 0
                braces_depth = 0
                is_multiplier = False
                multiplier_str = ''
                is_count = False
                count_str = ''
                is_term = True
            else:
                error_str = 'unparsable token'
            if error_str:
                raise ValueError(f"{error_str} at '{self.phrase_str}'[{i}]")
        if parentheses_depth:
            raise ValueError(f"unclosed parentheses in '{self.phrase_str}'")
        if braces_depth:
            raise ValueError(f"unclosed braces in '{self.phrase_str}'")


# recursive, lexemes not supported
def save_definition(phrase: AbstractPhrase, parent=None, index=0) -> models.Phrase:
    if isinstance(phrase, models.Phrase):
        return

    obj = models.Phrase.objects.create(
        parent = parent,
        index = index,
        has_braces = phrase.has_braces,
        tone_change = phrase.tone_change,
        suffix = phrase.suffix,
        multiplier = phrase.multiplier,
        count = phrase.count,
    )

    for i, child in enumerate(phrase.children):
        phrase.children[i].obj = save_definition(child, obj, i)
    
    return obj

