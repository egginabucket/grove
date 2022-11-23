from dataclasses import dataclass
from typing import Optional

from django.conf import settings
from jangle.models import LanguageTag
from music21.note import Rest, GeneralNote, Note
from music21.spanner import Slur
from music21.stream.iterator import StreamIterator
from music21.stream.base import Score, Stream
from music21.base import Music21Object
from nltk.corpus import wordnet2021

from carpet.base import AbstractPhrase, PitchChange, Suffix
from carpet.parser import StrPhrase
from maas.models import Lexeme
from maas.music import KIRA_SIZES, SizeMode, MaasMusicalContext
from maas.utils import EN, lexeme_from_en

# https://www.inspiredacoustics.com/en/MIDI_note_numbers_and_center_frequencies
# https://abjad.github.io/api/abjad/index.html#abjad

COUNT = lexeme_from_en("count")
NOT = lexeme_from_en("not")
WHAT = lexeme_from_en("what")


@dataclass
class CarpetContext(MaasMusicalContext):
    slur: bool = True
    lyrics_lang: Optional[LanguageTag] = None
    lexeme_fallback: Music21Object = Rest("half")
    """Used if no flex notes are defined for a lexeme."""

    def lexeme_to_stream(
        self, lexeme: Lexeme, exclude_ghosted=False
    ) -> Stream:
        flex_notes = lexeme.get_flex_notes()
        if exclude_ghosted:
            flex_notes = filter(lambda flex: not flex.is_ghosted, flex_notes)
        notes = [flex.get_note(self) for flex in flex_notes]
        stream = Score(notes or self.lexeme_fallback)
        if self.lyrics_lang is not None:
            general_notes: StreamIterator[
                GeneralNote
            ] = stream.getElementsByClass(GeneralNote)
            general_notes[0].addLyric(lexeme.translate(self.lyrics_lang), 1)
        return stream

    def phrase_to_stream(self, phrase: AbstractPhrase) -> Stream:
        stream = Score()
        if phrase.pitch_change:
            if phrase.pitch_change == PitchChange.UP:
                self.phrase_up()
            elif phrase.pitch_change == PitchChange.DOWN:
                self.phrase_down()
        core_stream = Score()

        children = list(phrase.modified_children())
        if phrase.lexeme:
            core_stream.append(self.lexeme_to_stream(phrase.lexeme))
        for child in children:
            core_stream.append(self.phrase_to_stream(child))
        stream.repeatAppend(core_stream, phrase.multiplier)

        if phrase.count:
            count_stream = self.lexeme_to_stream(COUNT, True)
            last_note = stream.recurse().notes.last() or count_stream.notes[-1]
            counting_note = Note()
            counting_note.pitches = last_note.pitches
            (
                counting_note.duration,
                counting_note.articulations,
            ) = self.sizes[SizeMode.MEDIUM]
            count_stream.repeatAppend(counting_note, phrase.count)
            stream.append(count_stream)
        if phrase.count == 0 or phrase.suffix == Suffix.NOT:
            stream.append(self.lexeme_to_stream(NOT, True))
        if phrase.suffix == Suffix.WHAT:
            stream.append(self.lexeme_to_stream(WHAT, True))
        stream = stream.flatten()
        if self.slur:
            stream.insert(0, Slur(stream.elements))
        return stream


def str_to_score(
    phrase_str: str,
    lang=EN,
    add_lyrics=True,
    *args,
    **kwargs,
) -> Score:
    ctx = CarpetContext(*args, **kwargs)
    if add_lyrics:
        ctx.lyrics_lang = lang
    phrase = StrPhrase(lang, wordnet2021, phrase_str)  # type: ignore
    stream = ctx.phrase_to_stream(phrase)
    return ctx.build_score(str(phrase), stream)
