# https://www.inspiredacoustics.com/en/MIDI_note_numbers_and_center_frequencies
# https://abjad.github.io/api/abjad/index.html#abjad

import abjad
from moss.models import Definition

DEFS_NUCLEUS = abjad.NamedPitch("c''")
SATELLITE_INTERVAL = 5
DOWN_INTERVAL = 3
UP_INTERVAL = 5

def carpet_to_lilypond(carpet_data: str, nucleus=DEFS_NUCLEUS):
    intervals_moved = 0
    for char in carpet_data:
    return