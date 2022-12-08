from __future__ import annotations

from dataclasses import dataclass, field
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
    pitch_change = None
    multiplier = 1
    count = None
    suffix = None
    lexeme: Optional[Lexeme] = None

    def get_children(self) -> Generator[AbstractPhrase, None, None]:
        ...

    def modified_children(self) -> Generator[AbstractPhrase, None, None]:
        children = list(self.get_children())
        for child in children:
            if child.is_primary or len(children) == 1:
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
        props["children"] = [c.serialize() for c in self.get_children()]
        return props

    def _unwrapped_str(self) -> str:
        if self.lexeme:
            return str(self.lexeme)
        else:
            return " ".join(map(str, self.get_children()))

    def __str__(self):
        open_str = ""
        close_str = ""
        if self.lexeme is None and not self.is_primary:
            open_str += OPEN_CHAR
        if self.is_primary:
            open_str += PRIMARY_OPEN_CHAR
            close_str += PRIMARY_CLOSE_CHAR
        if self.lexeme is None and not self.is_primary:
            close_str += CLOSE_CHAR
        if self.count:
            close_str += COUNT_CHAR + str(self.count)
        if self.multiplier != 1:
            close_str += MULTIPLIER_CHAR + str(self.multiplier)
        return "".join(
            filter(
                None,
                [
                    self.pitch_change,
                    open_str,
                    self._unwrapped_str(),
                    close_str,
                    self.suffix,
                ],
            )
        )

@dataclass(repr=False)
class BasePhrase(AbstractPhrase):
    children: list[AbstractPhrase] = field(default_factory=list)
    lexeme: Optional[Lexeme] = None
    is_primary: bool = False
    pitch_change: Optional[str] = None
    multiplier: int = 1
    count: Optional[int] = None
    suffix: Optional[str] = None

    def get_children(self) -> Generator[AbstractPhrase, None, None]:
        yield from self.children