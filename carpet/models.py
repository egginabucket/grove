from __future__ import annotations

from functools import cached_property
from typing import Generator

from django.db import models
from jangle.utils import BatchedCreateManager
from nltk.corpus.reader import Synset

from carpet.base import AbstractPhrase, PitchChange, Suffix
from carpet.wordnet import wordnet
from maas.models import Lexeme


class Phrase(models.Model, AbstractPhrase):
    child_rels: "models.manager.RelatedManager[PhraseComposition]"
    pitch_change = models.CharField(
        choices=PitchChange.choices,
        null=True,
        max_length=1,
    )  # type: ignore
    multiplier = models.PositiveSmallIntegerField(default=1)
    count = models.PositiveSmallIntegerField(null=True)  # type: ignore
    suffix = models.CharField(
        choices=Suffix.choices,
        null=True,
        max_length=1,
    )  # type: ignore
    lexeme = models.ForeignKey(
        Lexeme,
        null=True,
        on_delete=models.CASCADE,
    )  # type: ignore

    def _get_children(self) -> Generator[Phrase, None, None]:
        for child_rel in self.child_rels.order_by("index"):
            child_rel.child.is_primary = child_rel.is_primary
            yield child_rel.child

    def __str__(self) -> str:
        return AbstractPhrase.__str__(self)


class PhraseComposition(models.Model):
    parent = models.ForeignKey(
        Phrase,
        related_name="child_rels",
        on_delete=models.CASCADE,
    )
    child = models.ForeignKey(
        Phrase,
        related_name="parent_rels",
        on_delete=models.CASCADE,
    )
    index = models.SmallIntegerField()
    is_primary = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.parent.lexeme:
            raise ValueError(
                f"Parent already has a lexeme: '{self.parent.lexeme}'"
            )
        return super().save(*args, **kwargs)

    class Meta:
        unique_together = ("parent", "index")
        ordering = ["parent", "index"]


class SynsetDefQuerySet(models.QuerySet["SynsetDef"]):
    def from_synset(self, synset: Synset) -> SynsetDefQuerySet:
        return self.filter(pos=synset.pos(), wn_offset=synset.offset())

    def get_from_synset(self, synset: Synset) -> SynsetDef:
        return self.get(pos=synset.pos(), wn_offset=synset.offset())


class SynsetDefManager(BatchedCreateManager["SynsetDef"]):
    def get_queryset(self) -> SynsetDefQuerySet:
        return SynsetDefQuerySet(self.model, using=self._db)

    def from_synset(self, synset: Synset) -> SynsetDefQuerySet:
        return self.get_queryset().from_synset(synset)

    def get_from_synset(self, synset: Synset) -> SynsetDef:
        return self.get_queryset().get_from_synset(synset)


class SynsetDef(models.Model):
    """Links a WordNet synset to a Carpet phrase."""

    class WordnetPOS(models.TextChoices):
        ADJ = "a", "adjective"
        ADJ_SAT = "s", "satellite adjective"
        ADV = "r", "adverb"
        NOUN = "n", "noun"
        VERB = "v", "verb"

    pos = models.CharField(
        "part of speech",
        choices=WordnetPOS.choices,
        max_length=1,
    )
    wn_offset = models.PositiveBigIntegerField("offset")
    phrase = models.ForeignKey(
        Phrase,
        related_name="defined_synsets",
        on_delete=models.CASCADE,
    )
    source_file = models.CharField(null=True, max_length=254)

    @cached_property
    def synset(self) -> Synset:
        synset = wordnet.synset_from_pos_and_offset(self.pos, self.wn_offset)
        return synset  # type: ignore

    def __str__(self) -> str:
        return self.synset.name()  # type: ignore

    objects = SynsetDefManager()

    class Meta:
        verbose_name = "synset definition"
        unique_together = ("pos", "wn_offset")
