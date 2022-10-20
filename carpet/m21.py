# https://www.inspiredacoustics.com/en/MIDI_note_numbers_and_center_frequencies
# https://abjad.github.io/api/abjad/index.html#abjad

from typing import Tuple
from music21.stream.base import Stream, Score
from music21.key import Key, KeySignature
from music21.note import Note
from music21.duration import Duration
from music21.layout import Staff
from music21.tempo import MetronomeMark
from django.conf import settings
from language.models import Language, SpacyLanguageModel
from carpet.base import AbstractPhrase, PitchChange, Suffix, Depth
from carpet.models import apply_model_phrase, Term
from carpet.parser import StrPhrase

UP_DEGREE = 4
DOWN_DEGREE = -2

count_phrase = Term.objects.get(term='count', language=Language.native()).phrase
not_phrase = Term.objects.get(term='not', language=Language.native()).phrase
what_phrase = Term.objects.get(term='what', language=Language.native()).phrase
count_phrase.extend(Depth.LEXICAL, True)
not_phrase.extend(Depth.LEXICAL, True)
what_phrase.extend(Depth.LEXICAL, True)

def phrase_to_m21(phrase: AbstractPhrase, key: Key, nucleus_deg: int, add_lyrics=True) -> Tuple[Stream, int]:
    stream = Score()
    if phrase.pitch_change:
        if phrase.pitch_change == PitchChange.UP:
            nucleus_deg += UP_DEGREE
        elif phrase.pitch_change == PitchChange.DOWN:
            nucleus_deg += DOWN_DEGREE
    if lexeme := getattr(phrase, 'lexeme', None):
        lexeme_notes = [note.get_note(key, nucleus_deg)
            for note in lexeme.get_flex_notes()
        ]

        if add_lyrics and lexeme_notes:
            lexeme_notes[0].addLyric(lexeme.translation(phrase.lang))
        for note in lexeme_notes:
            #print(f"{nucleus_deg}, {note}")
            stream.append(note)
        
    for child in phrase.children:
        child_stream, nucleus_deg = phrase_to_m21(child, key, nucleus_deg, add_lyrics) #, i_voice_name)
        stream.append(child_stream)
    if phrase.count:
        count_stream, _ = phrase_to_m21(apply_model_phrase(phrase.lang, count_phrase), key, nucleus_deg, add_lyrics) #, i_voice_name)
        last_note: Note = stream.recurse().notes.last()
        last_note.duration = Duration('quarter')
        count_stream.repeatAppend(last_note, phrase.count)
        stream.append(last_note)
    if phrase.count == 0 or phrase.suffix == Suffix.NOT:
        not_stream, _ = phrase_to_m21(apply_model_phrase(phrase.lang, not_phrase), key, nucleus_deg, add_lyrics) #, i_voice_name)
        stream.append(not_stream)
    if phrase.suffix == Suffix.WHAT:
        what_stream, _ = phrase_to_m21(apply_model_phrase(phrase.lang, what_phrase), key, nucleus_deg, add_lyrics)
        stream.append(what_stream)
    
    parent_stream = Score()
    parent_stream.repeatAppend(stream, phrase.multiplier)
    return parent_stream.flatten(), nucleus_deg

def str_to_score(lang_m: SpacyLanguageModel, phrase_str: str, add_lyrics: bool, key=settings.DEFAULT_KEY) -> Score:
    lang_m.nlp
    phrase = StrPhrase(lang_m, phrase_str)
    phrase.extend(Depth.LEXICAL, True)
    phrase_stream, _ = phrase_to_m21(phrase, key, 0, add_lyrics)
    score = Score()
    """
    staff = stream()
    staff.append(KeySignature(key.sharps))
    staff.append(phrase_stream)
    score.append(staff)
    """
    score.append(MetronomeMark('allegro'))
    score.append(KeySignature(key.sharps))
    score.append(phrase_stream)
    return score.flatten()
    
