from typing import Generator
from mingus import intervals
from django.db import models
from common.models import PosTag
from maas import flex_notes

class Lexeme(models.Model):
    english = models.CharField(max_length=254, unique=True)
    notes = models.TextField(null=True) # notes notes, not musical notes!!

    def parse_flex_notes(self, raw_str: str) -> Generator[flex_notes]:
        for i, flex_note_str in enumerate(raw_str.strip().split()):
            flex_note = FlexNote(index=i, parent=self)
            flex_note.parse(flex_note_str)
            yield flex_note

    def get_flex_notes(self):
        return self.flex_notes.objects.order_by('index')

    def __str__(self):
        return self.english


class FlexNote(models.Model):    
    class Tone(models.TextChoices):
        NUCLEUS = 'N', 'nucleus'
        UPPER_SAT = 'U', 'upper satellite'
        LOWER_SAT = 'L', 'lower satellite'
    parent = models.ForeignKey(Lexeme, related_name='flex_notes', on_delete=models.CASCADE)
    index = models.PositiveSmallIntegerField()
    tone = models.SmallIntegerField(choices=flex_notes.Tone.choices)
    steps = models.SmallIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint('word', 'index', name='no_repeat_word_flex_note_indexes'),
        ]
    
    def parse(self, raw_str: str):
        self.tone = raw_str[0]
        if len(raw_str) > 1:
            self.steps = int(raw_str[1:])

    def __str__(self):
        self_str = str(self.tone)
        if self.steps:
            if self.steps > 0: self_str += '+'
            else: self_str += '-'
            self_str += abs(self.steps)
        return self_str