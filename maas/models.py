from typing import Generator
from django.db import models
from maas.flex_notes import AbstractFlexNote, Tone, DurationMode


# https://universaldependencies.org/u/pos/
# used in spacy, 'universal' tagset in nltk
class PosTag(models.Model):
    class Category(models.IntegerChoices):
        OPEN_CLASS = 0, 'open class'
        CLOSED_CLASS = 1, 'closed class'
        OTHER = 2, 'other'

    abbr = models.CharField(verbose_name='abbreviation', max_length=5)
    name = models.CharField(max_length=126)
    category = models.SmallIntegerField(choices=Category.choices)

    def __save__(self, *args, **kwargs):
        self.abbr = self.abbr.upper()
        self.description = self.description.lower()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.abbr
    
    class Meta:
        verbose_name = 'universal POS tag'


class FlexNote(models.Model, AbstractFlexNote):
    duration_mode = models.CharField(choices=DurationMode.choices, max_length=1)
    tone = models.CharField(choices=Tone.choices, max_length=1)
    degree = models.SmallIntegerField(default=0)
    is_ghosted = models.BooleanField(default=False)

    def __str__(self):
        return AbstractFlexNote.__str__(self)


class Lexeme(models.Model):
    english = models.CharField(max_length=254, unique=True)
    notes = models.TextField(null=True) # notes notes, not musical notes!!

    def parse_flex_notes(self, raw_str: str) -> Generator['LexemeFlexNote', None, None]:
        for i, flex_note_str in enumerate(raw_str.strip().split()):
            flex_note = LexemeFlexNote(index=i, lexeme=self)
            flex_note.parse(flex_note_str)
            yield flex_note

    def get_flex_notes(self) -> models.Manager['LexemeFlexNote']:
        return self.flex_notes.order_by('index')

    def __str__(self):
        return self.english


class LexemeFlexNote(FlexNote):
    flex_note = models.OneToOneField(FlexNote, parent_link=True, on_delete=models.CASCADE)
    lexeme = models.ForeignKey(Lexeme, related_name='flex_notes', on_delete=models.CASCADE)
    index = models.PositiveSmallIntegerField()

    def __str__(self):
        return f"{self.lexeme.english}/{self.index}: {self.flex_note}"

    class Meta:
        constraints = [
            models.UniqueConstraint('lexeme', 'index', name='no_repeat_lexeme_flex_notes'),
        ]