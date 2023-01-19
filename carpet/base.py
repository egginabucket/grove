from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Generator, Optional
import warnings

from django.db import models
from jangle.utils import StrReprCls

# from django.conf import settings
from maas.models import Lexeme

SYNSET_CHAR = "@"
MULTIPLIER_CHAR = "*"
COUNT_CHAR = "#"

OPEN_CHAR = "("
CLOSE_CHAR = ")"
PRIMARY_OPEN_CHAR = "["
PRIMARY_CLOSE_CHAR = "]"


class PitchChange(models.TextChoices):
    UP = "+", "up"
    DOWN = "-", "down"
    LAST = "$", "last"


class Suffix(models.TextChoices):
    WHAT = "?", "what"
    NOT = "!", "not"


class AbstractPhrase(StrReprCls):
    is_primary = False
    pitch_change: Optional[str] = None
    multiplier = 1
    count: Optional[int] = None
    suffix: Optional[str] = None
    lexeme: Optional[Lexeme] = None

    def _get_children(self) -> Generator[AbstractPhrase, None, None]:
        ...

    def modified_children(self) -> Generator[AbstractPhrase, None, None]:
        for child in self.children:
            if child.is_primary or len(self.children) == 1:
                child.multiplier *= self.multiplier
                if self.suffix:
                    if child.suffix:
                        warnings.warn(f"cannot add suffix to child")
                    else:
                        child.suffix = self.suffix
                        self.suffix = ""
                if self.count:
                    if child.count is None:
                        child.count = 1
                    child.count *= self.count
                    self.count = None
                self.multiplier = 1
            yield child

    def serialize(self) -> dict[str, Any]:
        props = {
            name: getattr(self, name)
            for name in [
                "is_primary",
                "pitch_change",
                "multiplier",
                "count",
                "suffix",
            ]
        }
        props["children"] = [c.serialize() for c in self.children]
        return props

    @cached_property
    def children(self) -> list[AbstractPhrase]:
        return list(self._get_children())

    def __str__(self):
        do_wrap = (
            self.lexeme is None
            and (not self.is_primary)
            and len(self.children) != 1
        )
        s = ""
        if self.pitch_change is not None:
            s += self.pitch_change
        if do_wrap:
            s += OPEN_CHAR
        if self.is_primary:
            s += PRIMARY_OPEN_CHAR
        if self.lexeme is not None:
            s += str(self.lexeme)
        else:
            s += " ".join(map(str, self.children))
        if self.is_primary:
            s += PRIMARY_CLOSE_CHAR
        if do_wrap:
            s += CLOSE_CHAR
        if self.multiplier != 1:
            s += MULTIPLIER_CHAR + str(self.multiplier)
        if self.suffix is not None:
            s += self.suffix
        return s

@dataclass(repr=False)
class BasePhrase(AbstractPhrase):
    children: list[AbstractPhrase] = field(default_factory=list)
    lexeme: Optional[Lexeme] = None
    is_primary: bool = False
    pitch_change: Optional[str] = None
    multiplier: int = 1
    count: Optional[int] = None
    suffix: Optional[str] = None
