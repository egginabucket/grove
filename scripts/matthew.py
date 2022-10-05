import os
import yaml
import abjad
try: from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader
from django.conf import settings
CORE_DEFS_PATH = os.path.join(settings.DICT_PATH, 'core.yaml')

#INTERVAL = abjad.NamedInterval('+M5')
DEFINITION_NUCLEUS = abjad.NamedPitch('c''')
KEY_SIGNATURE = abjad.KeySignature(abjad.NamedPitchClass('g'), abjad.Mode('major'))

key_quality = 'm' if KEY_SIGNATURE.mode == 'minor' else 'M'
INTERVAL = abjad.NumberedInterval(0) 
if KEY_SIGNATURE.tonic > DEFINITION_NUCLEUS.pitch_class:
    INTERVAL -= KEY_SIGNATURE.tonic - DEFINITION_NUCLEUS.pitch_class
else:
    INTERVAL -= DEFINITION_NUCLEUS.pitch_class - KEY_SIGNATURE.tonic

def run():
    with open(CORE_DEFS_PATH) as f:
        defs = yaml.load(f.read(), SafeLoader)
    while term := input('Enter term (Ctrl+C to exit): ').lower():
        if term in defs:
            print('Loading... Close window to run again')
            voice = abjad.Voice(defs[term])
            abjad.mutate.transpose(voice, INTERVAL)
            staff = abjad.Staff([voice])
            abjad.attach(KEY_SIGNATURE, staff[0][0])
            abjad.show(staff)
        else:
            print(f"Unknown term '{term}'")
