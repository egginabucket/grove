import math
from django.db import models
#from mingus.core import keys
#from mingus.containers import Note
from music21.note import Note
from music21.articulations import Staccato
from music21.duration import Duration
from music21.pitch import Pitch
from music21.key import Key
from music21.scale import Direction

UPPER_SAT_DEGREE = 4
LOWER_SAT_DEGREE = -4

GHOSTED_CHAR = '~'
"""
def key_interval(key: Key, note: Note, interval: int) -> Pitch:
    notes_in_key = keys.get_notes(key.key)
    for n in notes_in_key:
        if n[0] == note[0]:
            index = notes_in_key.index(n)
    total_interval = index + interval
    return Pitch(notes_in_key[total_interval % 7], octave=math.floor(total_interval / 7))
"""


class Tone(models.TextChoices):
    NUCLEUS = 'N', 'nucleus'
    UPPER_SAT = 'U', 'upper satellite'
    LOWER_SAT = 'L', 'lower satellite'


class DurationMode(models.TextChoices):
    WHOLE = '1', '1/1 note'
    QUARTER = '4', '1/4 note'
    STACCATO_QUARTER = '.', 'staccato 1/4 note'


class AbstractFlexNote:
    tone = Tone.NUCLEUS
    duration_mode = DurationMode.QUARTER
    degree = 0
    is_ghosted = False

    def parse(self, raw_str: str):
        if raw_str.startswith(GHOSTED_CHAR):
            self.is_ghosted = True
            raw_str = raw_str[1:]
        self.duration_mode = raw_str[0]
        self.tone = raw_str[1]
        if len(raw_str) > 2:
            self.degree = int(raw_str[2:])

    def __str__(self):
        self_str = self.duration_mode + str(self.tone)
        if self.is_ghosted:
            self_str = GHOSTED_CHAR + self_str
        if self.degree:
            if self.degree > 0:
                self_str += '+'
            else:
                self_str += '-'
            self_str += str(abs(self.degree))
        return self_str

    def get_pitch(self, key: Key, nucleus_degree: int) -> Pitch:
        degree = nucleus_degree
        if self.tone == Tone.UPPER_SAT:
            degree += UPPER_SAT_DEGREE
        elif self.tone == Tone.LOWER_SAT:
            degree += LOWER_SAT_DEGREE
        degree += self.degree
        pitch = key.pitchFromDegree(degree+1)
        pitch.octave += math.floor(degree / 7)
        return pitch

    def get_note(self, key: Key, nucleus_degree: degree) -> Note:
        pitch = self.get_pitch(key, nucleus_degree)
        note = Note(pitch)
        if self.duration_mode == DurationMode.WHOLE:
            note.duration = Duration('whole')
        elif self.duration_mode == DurationMode.QUARTER:
            note.duration = Duration('quarter')
        elif self.duration_mode == DurationMode.STACCATO_QUARTER:
            note.duration = Duration('quarter')
            note.articulations.append(Staccato())
        if self.is_ghosted:
            pass
        return note
