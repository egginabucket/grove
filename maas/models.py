from typing import Generator
from django.db import models
from language.models import Lang
from maas.flex_notes import AbstractFlexNote, Tone, DurationMode


class FlexNote(models.Model, AbstractFlexNote):
    duration_mode = models.CharField(
        choices=DurationMode.choices, max_length=1)
    tone = models.CharField(choices=Tone.choices, max_length=1)
    degree = models.SmallIntegerField(default=0)
    is_ghosted = models.BooleanField(default=False)

    def __str__(self):
        return AbstractFlexNote.__str__(self)


class Lexeme(models.Model):
    comment = models.TextField(null=True)

    def parse_flex_notes(self, raw_str: str) -> Generator['LexemeFlexNote', None, None]:
        for i, flex_note_str in enumerate(raw_str.strip().split()):
            flex_note = LexemeFlexNote(index=i, lexeme=self)
            flex_note.parse(flex_note_str)
            yield flex_note

    def get_flex_notes(self) -> models.Manager['LexemeFlexNote']:
        return self.flex_notes.order_by('index')

    def translation(self, lang: Lang) -> str:
        return self.translations.get(lang=lang).term

    def __str__(self):
        return self.translation(Lang.native())


class LexemeTranslation(models.Model):
    lexeme = models.ForeignKey(
        Lexeme, related_name='translations', on_delete=models.CASCADE)
    term = models.CharField(max_length=254)
    lang = models.ForeignKey(Lang, on_delete=models.PROTECT)

    def __str__(self):
        return self.term

    class Meta:
        unique_together = ('lexeme', 'lang')


class LexemeFlexNote(FlexNote):
    flex_note = models.OneToOneField(
        FlexNote, parent_link=True, on_delete=models.CASCADE)
    lexeme = models.ForeignKey(
        Lexeme, related_name='flex_notes', on_delete=models.CASCADE)
    index = models.PositiveSmallIntegerField()

    def __str__(self):
        return f"{self.lexeme.english}/{self.index}: {self.flex_note}"

    class Meta:
        unique_together = ('lexeme', 'index')
