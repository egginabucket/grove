import enum
from typing import Generator
from string import ascii_letters


TERM_CHARS = ascii_letters + ':_\''
MULTIPLIER_CHAR = '*'
COUNT_CHAR = '#'
SHOW_BRACES = False
SHOW_PARANTHESES = False

class Depth(enum.IntEnum):
    SIMPLE = 0
    SHALLOW = 1
    RECURSIVE = 2
    VOCAB = 3
    LEXICAL = 4


class AbstractPhrase:
    phrase_str = ''
    def extend(self, depth: Depth, movemodifiers: bool):
        if depth < Depth.SHALLOW:
            return
        self.children = list(self.get_children()) # sets children and def from subclass
        if movemodifiers:
            self.move_modifiers()
        if depth < Depth.LEXICAL and hasattr(self, 'defined_term'):
            return
        if depth < Depth.RECURSIVE:
            return
        for i, child in enumerate(self.children):
            if issubclass(type(child), AbstractPhrase):
                if depth >= Depth.RECURSIVE:
                    child.extend(depth, movemodifiers)

    def move_modifiers(self):
        for i, child in enumerate(self.children):
            if issubclass(type(child), AbstractPhrase):
                if child.has_braces or len(self.children) == 1:
                    self.children[i].multiplier *= self.multiplier
                    if self.suffix:
                        if self.childen[i].suffix:
                            raise ValueError(f"cannot add suffix to child")
                        self.children[i].suffix = self.suffix
                        self.suffix = ''
                    if self.count:
                        if child.count is None:
                            child.count = 1
                        child.count *= self.count
                        self.count = None
                    self.multiplier = 1
    
    def get_children(self) -> Generator['AbstractPhrase']:
        yield
    
    def unwrapped_str(self) -> str:
        return ' '.join(map(str, self.children)) or self.phrase_str
    
    def __str__(self):
        start_str = ''
        end_str = ''
        if SHOW_BRACES and self.has_braces:
            start_str += '{'
            end_str += '}'
        elif SHOW_PARANTHESES or self.suffix and ' ' in self.phrase:
            start_str += '('
            end_str += ')'
        if self.count:
            end_str += '#' + str(self.count)
        return ((self.tone_change or '' +
            start_str +
            self.unwrapped_str() +
            end_str +
            self.suffix +
            ' ') * self.multiplier)[:-1]
    
    def __repr__(self):
        return f"<{type(self).__name__}: '{str(self)}'>"

