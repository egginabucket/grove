import os
import yaml
from django.conf import settings
from language.models import IsoLang
from maas.models import Lexeme, LexemeTranslation  # , LexemeFlexNote

LEXICON_PATH = os.path.join('maas', 'lexicon')


def register_translated_lexicon(path: str, iso_lang: IsoLang, native_lang=IsoLang.native()):
    with open(path) as f:
        LexemeTranslation.objects.bulk_create(LexemeTranslation(
            lexeme=LexemeTranslation.objects.get(
                iso_lang=native_lang, term=native_term).lexeme,
            term=translated_term,
            iso_lang=iso_lang,
        ) for native_term, translated_term in yaml.load(f.read(), settings.YAML_LOADER))


def register_full_lexicon(path=LEXICON_PATH, native_lang=IsoLang.native(), clear=True):
    if clear:
        Lexeme.objects.all().delete()
    native_lexemes = []
    with open(os.path.join(path, 'native.yaml')) as f:
        flex_notes = []
        for native_word, raw_notes in yaml.load(f.read(), settings.YAML_LOADER).items():
            lexeme = Lexeme.objects.create()
            native_lexemes.append(LexemeTranslation(
                lexeme=lexeme,
                word=native_word,
                iso_lang=native_lang,
            ))
            flex_notes.extend(lexeme.parse_flex_notes(raw_notes))
        # bulk_create no longer works with inherited model
        for flex_note in flex_notes:
            flex_note.save()
    LexemeTranslation.objects.bulk_create(native_lexemes)
    for fn in os.listdir(path):
        full_path = os.path.join(path, fn)
        if os.path.isfile(full_path) and full_path.endswith('.yaml'):
            lang_code = fn.split('.')[0]
            if lang_code == 'native':
                continue
            register_translated_lexicon(
                full_path,
                IsoLang.objects.get(code=lang_code),
                native_lang
            )
