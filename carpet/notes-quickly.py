# https://www.inspiredacoustics.com/en/MIDI_note_numbers_and_center_frequencies
# https://abjad.github.io/api/abjad/index.html#abjad

import fractions
import parce.transform
from mingus.core import intervals
from quickly import pitch, key, duration, transpose
from quickly.dom import lily
from quickly.lang import lilypond
from moss.carpet import AbstractPhrase, Depth, StrPhrase
from moss.models import CarpetPhrase, Definition


DEFINITION_NUCLEUS = pitch.Pitch(2, 'c')
DEFAULT_KEY_SIGNATURE = key.KeySignature('b', mode='major')
UPPER_SATELLITE_INTERVAL = intervals.fifth
LOWER_SATELLITE_INTERVAL = intervals.fourth
UP_INTERVAL = intervals.fifth
DOWN_INTERVAL = intervals.fourth
COUNT_EXTEND_DURATION = lily.Duration(fractions.Fraction(1, 4))
count_phrase = AbstractPhrase(def_obj=Definition.objects.get(term='count'))
not_phrase = AbstractPhrase(def_obj=Definition.objects.get(term='not'))
count_phrase.extend(Depth.EXTEND_VOCAB, True)
not_phrase.extend(Depth.EXTEND_VOCAB, True)

lily.Note('c')
transpose.MAJOR_SCALE

"""
def get_first_durable(music: lily.MusicList) -> lily.Durable:
    for component in music:
        if issubclass(type(component), lily.Durable):
            return component
        else:
            return get_first_leaf(component)
"""


def get_last_note(music: lily.MusicList) -> lily.Note | None:
    a = (reversed(music) // lily.Note)
    for component in reversed(music) // lily.Note:
        if issubclass(type(component), lily.Note):
            return component
        if music.is_sequential():
            if note := get_last_note(component):
                return note
    return None

def carpet_to_lilypond(phrase: AbstractPhrase, interval=abjad.NumberedInterval(0), add_lyrics=True, voice_name='') -> tuple[lily.Musiclist, abjad.Interval]:
    for i in range(phrase.multiplier):
        i_voice_name = f"{voice_name}_{i}"
        if phrase.tone_change:
            if phrase.tone_change == CarpetPhrase.ToneChange.UP:
                interval += UP_INTERVAL
            elif phrase.tone_change == CarpetPhrase.ToneChange.DOWN:
                interval += DOWN_INTERVAL
        if core_def := getattr(phrase.def_obj, 'core_synonym', None):
            term_music = lilycore_def.phrase
            abjad.mutate.transpose(term_voice, interval)
            music.extend(term_voice)
            if add_lyrics:
                lyricsto_contents_container = abjad.Container()
                abjad.attach(abjad.LilyPondLiteral('"'+core_def.term+'"'), lyricsto_contents_container)
                lyricsto_container = abjad.Container([lyricsto_contents_container])
                abjad.attach(abjad.LilyPondLiteral(r"\lyricsto"+ f' "{i_voice_name}"', 'absolute_before'), lyricsto_container)
                lyrics_container = abjad.Container([lyricsto_container]),# tag=abjad.Tag('new Lyrics'))
                abjad.attach(abjad.Markup(r"\new Lyrics", 'absolute_before'), lyrics_container)
                container.append(lyrics_container)
        for child in phrase.children:
            child_container, interval = carpet_to_abjad(child, interval, add_lyrics, i_voice_name)
            container.append(child_container)
        if phrase.count:
            count_container, _ = carpet_to_abjad(count_phrase, interval, add_lyrics, i_voice_name)
            last_note: abjad.Note = abjad.mutate.copy(get_last_note(container))
            last_note.written_duration = lily.Fraction()
            #abjad.mutate.transpose(last_note, interval)
            for _ in range(phrase.count):
                count_container.append(abjad.mutate.copy(last_note))
            container.append(count_container)
        if phrase.count == 0 or phrase.suffix == CarpetPhrase.Suffix.NOT:
            not_container, _ = carpet_to_abjad(not_phrase, interval, add_lyrics, i_voice_name)
            container.append(not_container)
    return container, interval

def show_carpet_str(phrase_str: str, add_lyrics: bool, key_signature = DEFAULT_KEY_SIGNATURE):
    phrase = StrPhrase(phrase_str)
    phrase.extend(Depth.EXTEND_VOCAB, True)
    interval = key_signature.tonic.number - DEFINITION_NUCLEUS.pitch_class.number
    while interval > 6:
        interval -= 12
    container, interval = carpet_to_abjad(phrase, interval, add_lyrics)

    staff = abjad.Staff([container])
    abjad.attach(key_signature, get_first_leaf(staff))
    staff.append(container)
    abjad.show(staff)
    return container

