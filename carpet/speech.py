from music21.note import Note
from music21.spanner import Slur
from music21.stream.base import Score, Stream

from carpet.base import AbstractPhrase, PitchChange, Suffix
from carpet.parser import StrPhrase
from maas.speech import MaasContext, MaasSpeech, SizeMode
from maas.utils import EN, lexeme_from_en

# https://www.inspiredacoustics.com/en/MIDI_note_numbers_and_center_frequencies
# https://abjad.github.io/api/abjad/index.html#abjad

COUNT = lexeme_from_en("count")
NOT = lexeme_from_en("not")
WHAT = lexeme_from_en("what")


class CarpetSpeech(MaasSpeech):
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
            core_stream.append(phrase.lexeme.stream(self))
        for child in children:
            core_stream.append(self.phrase_to_stream(child))
        stream.repeatAppend(core_stream, phrase.multiplier)

        if phrase.count:
            count_stream = COUNT.stream(self, True)
            last_note = stream.recurse().notes.last() or count_stream.notes[-1]
            counting_note = Note()
            counting_note.pitches = last_note.pitches
            (
                counting_note.duration,
                counting_note.articulations,
            ) = self.ctx.sizes[SizeMode.MEDIUM]
            count_stream.repeatAppend(counting_note, phrase.count)
            stream.append(count_stream)
        if phrase.count == 0 or phrase.suffix == Suffix.NOT:
            stream.append(NOT.stream(self, True))
        if phrase.suffix == Suffix.WHAT:
            stream.append(WHAT.stream(self, True))
        stream = stream.flatten()
        if self.ctx.write_slurs:
            stream.insert(0, Slur(stream.elements))
        return stream

def str_to_score(
    ctx: MaasContext,
    phrase_str: str,
    lang = EN,
    add_lyrics = False
) -> Score:
    if add_lyrics:
        ctx.lyrics_lang = lang
    phrase = StrPhrase(lang, phrase_str)
    speech = CarpetSpeech(ctx)
    stream = speech.phrase_to_stream(phrase)
    return ctx.build_score(str(phrase), stream)
