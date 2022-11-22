import math
import re
from dataclasses import dataclass, field
from typing import Optional, Tuple

from django.conf import settings
from django.db import models
from jangle.models import LanguageTag

from music21.key import KeySignature
from music21.metadata import Metadata
from music21.meter.base import SenzaMisuraTimeSignature, TimeSignature
from music21.stream.base import Part, Score, Stream
from music21.articulations import Articulation, Staccato
from music21.duration import Duration
from music21.key import Key
from music21.note import Note
from music21.pitch import Pitch

UPPER_SAT_DEGREE = 4
LOWER_SAT_DEGREE = -4

UP_DEGREE = 4
DOWN_DEGREE = -2

GHOSTED_TOKEN = "~"


class Tone(models.TextChoices):
    NUCLEUS = "N", "nucleus"
    UPPER_SAT = "U", "upper satellite"
    LOWER_SAT = "L", "lower satellite"


class DurationMode(models.TextChoices):
    WHOLE = "1", "1/1 note"
    QUARTER = "4", "1/4 note"
    STACCATO_QUARTER = ".", "staccato 1/4 note"


DurationMappings = dict[DurationMode, Tuple[Duration, list[Articulation]]]


DEFAULT_DURATION_MAPPINGS: DurationMappings = {
    DurationMode.WHOLE: (Duration("whole"), []),
    DurationMode.QUARTER: (Duration("quarter"), []),
    DurationMode.STACCATO_QUARTER: (Duration("quarter"), [Staccato()]),
}
HALF_MAPPINGS: DurationMappings = {
    DurationMode.WHOLE: (Duration("half"), []),
    DurationMode.QUARTER: (Duration("quarter"), []),
    DurationMode.STACCATO_QUARTER: (Duration("eighth"), []),
}


FLEX_NOTE_RE = re.compile(
    r"(?P<ghosted>%s)?(?P<duration_mode>[%s])(?P<tone>[%s])(?P<degree>[+-]\d+)?"
    % (
        re.escape(GHOSTED_TOKEN),
        re.escape("".join(DurationMode.values)),
        "".join(Tone.values),
    )
)


@dataclass
class MaasMusicalContext:
    key: Key = settings.DEFAULT_KEY
    duration_mappings: DurationMappings = field(
        default_factory=(lambda: DEFAULT_DURATION_MAPPINGS)
    )
    upper_sat_degree = 4
    lower_sat_degree = 4
    phrase_down_degree = -2
    phrase_up_degree = +4
    _degree = 0

    def reset_phrase(self) -> None:
        self._degree = 0

    def phrase_down(self) -> None:
        self._degree += self.phrase_down_degree

    def phrase_up(self) -> None:
        self._degree += self.phrase_up_degree

    def build_score(self, title: str, stream: Stream) -> Score:
        part = Part()
        # part.append(MetronomeMark(number=240))
        part.append(KeySignature(self.key.sharps))
        part.append(TimeSignature("16/1"))
        part.append(SenzaMisuraTimeSignature("0"))
        part.append(stream)
        md = Metadata()
        md.composer = "Grove / Null Identity"
        md.title = title
        score = Score()
        score.insert(0, md)
        score.append(part)
        return score.flatten()


class AbstractFlexNote:
    tone = Tone.NUCLEUS
    duration_mode = DurationMode.QUARTER
    degree = 0
    is_ghosted = False

    def from_match(self, match: re.Match[str]) -> None:
        groups = match.groupdict("")
        self.is_ghosted = bool(groups["ghosted"])
        self.duration_mode = DurationMode(groups["duration_mode"])
        self.tone = groups["tone"]
        if degree := groups["degree"]:
            self.degree = int(degree)
        else:
            self.degree = 0

    def __str__(self):
        self_str = self.duration_mode + str(self.tone)
        if self.is_ghosted:
            self_str = GHOSTED_TOKEN + self_str
        if self.degree:
            if self.degree > 0:
                self_str += "+"
            else:
                self_str += "-"
            self_str += str(abs(self.degree))
        return self_str

    def get_pitch(self, ctx: MaasMusicalContext) -> Pitch:
        degree = ctx._degree  # TODO: Move
        if self.tone == Tone.UPPER_SAT:
            degree += UPPER_SAT_DEGREE
        elif self.tone == Tone.LOWER_SAT:
            degree += LOWER_SAT_DEGREE
        degree += self.degree
        pitch = ctx.key.pitchFromDegree((degree % 7) + 1)
        if pitch is None:
            raise ValueError(f"could not get pitch from degree {degree}")
        pitch.octave = pitch.implicitOctave + (math.floor(degree / 7))
        return pitch

    def get_note(self, ctx: MaasMusicalContext) -> Note:
        pitch = self.get_pitch(ctx)
        note = Note(pitch)
        note.duration, note.articulations = ctx.duration_mappings[
            self.duration_mode
        ]
        if self.is_ghosted:
            pass
        return note
