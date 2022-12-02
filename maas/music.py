import math
import re
from dataclasses import dataclass, field
from typing import Optional, Tuple

from django.conf import settings
from django.db import models
from jangle.models import LanguageTag
from music21.articulations import Articulation, Staccato
from music21.base import Music21Object
from music21.duration import Duration
from music21.key import Key, KeySignature
from music21.metadata import Metadata
from music21.meter.base import SenzaMisuraTimeSignature, TimeSignature
from music21.note import Note, Rest
from music21.pitch import Pitch
from music21.stream.base import Part, Score, Stream

UPPER_SAT_DEGREE = 4
LOWER_SAT_DEGREE = -4

UP_DEGREE = 4
DOWN_DEGREE = -2

GHOSTED_TOKEN = "~"


class Tone(models.TextChoices):
    NUCLEUS = "N", "nucleus"
    UPPER_SAT = "U", "upper satellite"
    LOWER_SAT = "L", "lower satellite"


class SizeMode(models.TextChoices):
    """Includes durations and articulations."""

    LARGE = "1", "large (whole) note"
    MEDIUM = "4", "medium (1/4) note"
    SMALL = ".", "small (staccato 1/4) note"


SizeMappings = dict[SizeMode, Tuple[Duration, list[Articulation]]]


ORIGINAL_SIZES: SizeMappings = {
    SizeMode.LARGE: (Duration("whole"), []),
    SizeMode.MEDIUM: (Duration("quarter"), []),
    SizeMode.SMALL: (Duration("quarter"), [Staccato()]),
}
HALVED_SIZES: SizeMappings = {
    SizeMode.LARGE: (Duration("half"), []),
    SizeMode.MEDIUM: (Duration("quarter"), []),
    SizeMode.SMALL: (Duration("eighth"), []),
}
KIRA_SIZES: SizeMappings = {
    SizeMode.LARGE: (Duration("half"), []),
    SizeMode.MEDIUM: (Duration("quarter"), []),
    SizeMode.SMALL: (Duration("quarter"), [Staccato()]),
}


FLEX_NOTE_RE = re.compile(
    r"(?P<ghosted>%s)?(?P<duration_mode>[%s])(?P<tone>[%s])(?P<degree>[+-]\d+)?"
    % (
        re.escape(GHOSTED_TOKEN),
        re.escape("".join(SizeMode.values)),
        "".join(Tone.values),
    )
)


@dataclass
class MaasContext:
    key: Key = settings.DEFAULT_KEY
    sizes: SizeMappings = field(default_factory=lambda: KIRA_SIZES)
    degree_offset = 0
    upper_sat_degree = +4
    lower_sat_degree = -4
    phrase_down_degree = -2
    phrase_up_degree = +4
    write_slurs: bool = True
    lyrics_lang: Optional[LanguageTag] = None
    lexeme_fallback: Music21Object = Rest("half")
    """Used if no flex notes are defined for a lexeme."""
    gender_pronouns: bool = True
    peri_rest: float = 4.0
    comm_rest: float = 1.0

    def build_score(self, title: str, stream: Stream) -> Score:
        part = Part()
        # part.append(MetronomeMark(number=240))
        part.append(KeySignature(self.key.sharps))
        part.append(TimeSignature("16/1"))
        #part.append(SenzaMisuraTimeSignature("0"))
        part.append(stream)
        md = Metadata()
        md.composer = "Grove / Null Identity"
        md.title = title
        score = Score()
        score.insert(0, md)
        score.append(part)
        return score.flatten()


class MaasSpeech:
    ctx: MaasContext
    _degree = 0

    def __init__(self, ctx: MaasContext):
        self.ctx = ctx
        self.reset_phrase()

    def reset_phrase(self) -> None:
        self._degree = self.ctx.degree_offset

    @property
    def degree(self) -> int:
        return self._degree

    def phrase_down(self) -> None:
        self._degree += self.ctx.phrase_down_degree

    def phrase_up(self) -> None:
        self._degree += self.ctx.phrase_up_degree


class AbstractFlexNote:
    tone = Tone.NUCLEUS
    size_mode = SizeMode.MEDIUM
    degree = 0
    is_ghosted = False

    def from_match(self, match: re.Match[str]) -> None:
        groups = match.groupdict("")
        self.is_ghosted = bool(groups["ghosted"])
        self.size_mode = SizeMode(groups["duration_mode"])
        self.tone = groups["tone"]
        if degree := groups["degree"]:
            self.degree = int(degree)
        else:
            self.degree = 0

    def __str__(self):
        self_str = self.size_mode + str(self.tone)
        if self.is_ghosted:
            self_str = GHOSTED_TOKEN + self_str
        if self.degree:
            if self.degree > 0:
                self_str += "+"
            else:
                self_str += "-"
            self_str += str(abs(self.degree))
        return self_str

    def get_pitch(self, speech: MaasSpeech) -> Pitch:
        degree = speech.degree
        if self.tone == Tone.UPPER_SAT:
            degree += speech.ctx.upper_sat_degree
        elif self.tone == Tone.LOWER_SAT:
            degree += speech.ctx.lower_sat_degree
        degree += self.degree
        pitch = speech.ctx.key.pitchFromDegree((degree % 7) + 1)
        if pitch is None:
            raise ValueError(f"could not get pitch from degree {degree}")
        pitch.octave = pitch.implicitOctave + (math.floor(degree / 7))
        return pitch

    def get_note(self, speech: MaasSpeech) -> Note:
        pitch = self.get_pitch(speech)
        note = Note(pitch)
        note.duration, note.articulations = speech.ctx.sizes[self.size_mode]
        if self.is_ghosted:
            pass
        return note
