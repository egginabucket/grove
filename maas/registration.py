import os
import yaml
from django.conf import settings
from maas.models import PosTag, Lexeme, LexemeFlexNote

LEXICON_PATH = os.path.join('maas', 'lexicon.yaml')
UNIVERSAL_POS_PATH = os.path.join('maas', 'universal_pos.yaml')

def register_pos_tags(path=UNIVERSAL_POS_PATH, clear=True):
    if clear:
        PosTag.objects.all().delete()
    with open(path) as f:
        pos_tags = []
        for cat, tags in yaml.load(f.read(), settings.YAML_LOADER).items():
            category = PosTag.Category.OTHER
            for i, choice in PosTag.Category.choices:
                if cat == choice:
                    category = i
                    break
            for abbr, name in tags.items():
                pos_tags.append(PosTag(abbr=abbr, name=name, category=category))
        PosTag.objects.bulk_create(pos_tags)

def register_lexicon(path=LEXICON_PATH, clear=True):
    if clear:
        Lexeme.objects.all().delete()
    with open(path) as f:
        defs = yaml.load(f.read(), settings.YAML_LOADER)
        flex_notes = []
        for english, raw_notes in defs.items():
            lexeme = Lexeme.objects.create(english=english)
            flex_notes.extend(lexeme.parse_flex_notes(raw_notes))
        # bulk_create no longer works with inherited model
        for flex_note in flex_notes:
            flex_note.save()
