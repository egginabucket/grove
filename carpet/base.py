import enum
from typing import Generator, Optional
#from string import ascii_letters
from django.db import models
#from django.conf import settings
from language.models import Language

#TERM_CHARS = ascii_letters + ':_\''
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

class PitchChange(models.TextChoices):
    UP = '+', 'up'
    DOWN = '-', 'down'
    LAST = '@', 'last'

class Suffix(models.TextChoices):
    WHAT = '?', 'what'
    NOT = '!', 'not'

class AbstractPhrase:
    lang: Language = None
    has_braces = False
    pitch_change = None
    multiplier = 1
    count = None
    suffix = None
    children = []

    def extend(self, depth: Depth, move_modifiers: bool):
        if depth < Depth.SHALLOW:
            return
        self.children = list(self.get_children()) # sets children and def from subclass
        if move_modifiers:
            self.move_modifiers()
        if depth < Depth.LEXICAL and hasattr(self, 'defined_term'):
            return
        if depth < Depth.RECURSIVE:
            return
        for child in self.children:
            if isinstance(child, AbstractPhrase):
                if depth >= Depth.RECURSIVE:
                    child.extend(depth, move_modifiers)

    def move_modifiers(self):
        for i, child in enumerate(self.children):
            if isinstance(child, AbstractPhrase):
                if child.has_braces or len(self.children) == 1:
                    self.children[i].multiplier *= self.multiplier
                    if self.suffix:
                        if self.children[i].suffix:
                            raise ValueError(f"cannot add suffix to child")
                        self.children[i].suffix = self.suffix
                        self.suffix = ''
                    if self.count:
                        if child.count is None:
                            child.count = 1
                        child.count *= self.count
                        self.count = None
                    self.multiplier = 1
            else: continue # TODO
    
    def get_children(self) -> Generator['AbstractPhrase', None, None]:
        yield from []
    
    def serialize(self) -> dict[str]:
        props =  {name:getattr(self, name) for name in [
            'has_braces', 'pitch_change', 'multiplier', 'count', 'suffix'
        ]}
        props['children'] = [c.serialize() for c in self.children]
        return props
    
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
        return ((self.pitch_change or '' +
            start_str +
            self.unwrapped_str() +
            end_str +
            self.suffix +
            ' ') * self.multiplier)[:-1]
    
    def __repr__(self):
        return f"<{type(self).__name__}: '{str(self)}'>"
