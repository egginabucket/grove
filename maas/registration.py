import os
import yaml
from django.conf import settings
from language.models import Language
from maas.models import Lexeme, LexemeTranslation #, LexemeFlexNote

LEXICON_PATH = os.path.join('maas', 'lexicon')

def register_translated_lexicon(path: str, language: Language, native_lang=Language.native()):
    lexeme_translations = []
    with open(path) as f:
        for native_term, translated_term in yaml.load(f.read(), settings.YAML_LOADER):
            lexeme_translations.append(LexemeTranslation(
                lexeme = LexemeTranslation.objects.get(language=native_lang, term=native_term).lexeme,
                term = translated_term,
                language = language,
            ))
    LexemeTranslation.objects.bulk_create(lexeme_translations)

def register_full_lexicon(path=LEXICON_PATH, native_lang=Language.native(), clear=True):
    if clear:
        Lexeme.objects.all().delete()
    native_lexemes = []
    with open(os.path.join(path, 'native.yaml')) as f:
        flex_notes = []
        for native_term, raw_notes in yaml.load(f.read(), settings.YAML_LOADER).items():
            lexeme = Lexeme.objects.create()
            native_lexemes.append(LexemeTranslation(
                lexeme = lexeme,
                term = native_term,
                language = native_lang,
            ))
            flex_notes.extend(lexeme.parse_flex_notes(raw_notes))
        # bulk_create no longer works with inherited model
        for flex_note in flex_notes:
            flex_note.save()
    LexemeTranslation.objects.bulk_create(native_lexemes)
    for fn in os.listdir(path):
        full_path = os.path.join(path, fn)
        if os.path.isfile(full_path) and full_path.endswith('.yaml'):
            language_code = fn.split('.')[0]
            if language_code == 'native': continue
            register_translated_lexicon(full_path,
                Language.objects.get(code=language_code),
                native_lang,
            )
