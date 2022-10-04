# https://www.inspiredacoustics.com/en/MIDI_note_numbers_and_center_frequencies
# https://abjad.github.io/api/abjad/index.html#abjad

import abjad
from moss.carpet import AbstractParentPhrase
from moss.models import Definition

DEFS_NUCLEUS = abjad.NamedPitch("c''")
SATELLITE_INTERVAL = 5
DOWN_INTERVAL = 3
UP_INTERVAL = 5

class PhraseNotes:
    nucleus = DEFS_NUCLEUS
    intervals_moved = 0
    


def carpet_to_lilypond(carpet: AbstractParentPhrase, phrase=PhraseNotes):
    if hasattr(phrase, 'def_obj') and phrase.def_obj.core_synonym:
        return
