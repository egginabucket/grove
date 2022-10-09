# https://www.inspiredacoustics.com/en/MIDI_note_numbers_and_center_frequencies
# https://abjad.github.io/api/abjad/index.html#abjad

from typing import Tuple
from music21.key import Key, KeySignature
from music21.note import Note
from music21.duration import Duration
from music21.stream.base import Stream, Part, Score
from carpet.common import AbstractPhrase, PitchChange, Suffix, Depth
from carpet.models import Phrase
from carpet.parser import StrPhrase

def testing():
    n = Note()
    n.addLyric('what')
    s = Stream()

UP_DEGREE = 4
DOWN_DEGREE = -2
DEFAULT_KEY = Key('B')

count_phrase = Phrase.objects.get(lexeme__english='count')
not_phrase = Phrase.objects.get(lexeme__english='not')
count_phrase.extend(Depth.LEXICAL, True)
not_phrase.extend(Depth.LEXICAL, True)

def carpet_to_m21(phrase: AbstractPhrase, key: Key, nucleus_deg: int, add_lyrics=True) -> Tuple[Part, int]:
    part = Score()
    #i_voice_name = f"{voice_name}_{i}"
    if phrase.pitch_change:
        if phrase.pitch_change == PitchChange.UP:
            nucleus_deg += UP_DEGREE
        elif phrase.pitch_change == PitchChange.DOWN:
            nucleus_deg += DOWN_DEGREE
    if phrase.lexeme:
        lexeme_notes = [note.get_note(key, nucleus_deg)
            for note in phrase.lexeme.get_flex_notes()
        ]

        if add_lyrics and lexeme_notes:
            lexeme_notes[0].addLyric(phrase.lexeme.english)
        for note in lexeme_notes:
            print(f"{nucleus_deg}, {note}")
            part.append(note)
        """
        if add_lyrics:
            lyricsto_contents_container = abjad.Container()
            abjad.attach(abjad.LilyPondLiteral('"'+core_def.term+'"'), lyricsto_contents_container)
            lyricsto_container = abjad.Container([lyricsto_contents_container])
            abjad.attach(abjad.LilyPondLiteral(r"\lyricsto"+ f' "{i_voice_name}"', 'absolute_before'), lyricsto_container)
            lyrics_container = abjad.Container([lyricsto_container]),# tag=abjad.Tag('new Lyrics'))
            abjad.attach(abjad.Markup(r"\new Lyrics", 'absolute_before'), lyrics_container)
            container.append(lyrics_container)
        """
    for child in phrase.children:
        child_part, nucleus_deg = carpet_to_m21(child, key, nucleus_deg, add_lyrics) #, i_voice_name)
        part.append(child_part)
    if phrase.count:
        count_part, _ = carpet_to_m21(count_phrase, key, nucleus_deg, add_lyrics) #, i_voice_name)
        last_note: Note = part.recurse().notes.last()
        last_note.duration = Duration('quarter')
        count_part.repeatAppend(last_note, phrase.count)
        part.append(last_note)
    if phrase.count == 0 or phrase.suffix == Suffix.NOT:
        not_part, _ = carpet_to_m21(not_phrase, key, nucleus_deg, add_lyrics) #, i_voice_name)
        part.append(not_part)
    parent_part = Score()
    parent_part.repeatAppend(part, phrase.multiplier)
    return parent_part, nucleus_deg

def show_carpet_str(phrase_str: str, add_lyrics: bool, key=DEFAULT_KEY) -> Score:
    phrase = StrPhrase(phrase_str)
    phrase.extend(Depth.LEXICAL, True)
    part, _ = carpet_to_m21(phrase, key, 0, add_lyrics)
    score = Score()
    score.append(Score(KeySignature(key.sharps)))
    score.append(part)
    score.write('musicxml', 'where')
    score.show(fmt='lily')
    return score

