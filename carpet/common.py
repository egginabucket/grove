import enum
from typing import Generator, Optional
from string import ascii_letters
import spacy
from django.db import models
from django.conf import settings
from maas.models import Lexeme

nlp = spacy.load(settings.SPACY_PACKAGE)

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

class PitchChange(models.TextChoices):
    UP = '+', 'up'
    DOWN = '-', 'down'
    LAST = '@', 'last'


class Suffix(models.TextChoices):
    QUESTION = '?', 'question'
    NOT = '!', 'not'


class AbstractPhrase:
    has_braces = False
    pitch_change = None
    multiplier = 1
    count = None
    suffix = None
    lexeme: Optional[Lexeme] = None

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
        for child in self.children:
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
    
    def get_children(self) -> Generator['AbstractPhrase', None, None]:  pass
    
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

