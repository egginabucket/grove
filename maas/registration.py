import os
import yaml
from django.conf import settings
from jangle.models import LanguageTag
from maas.utils import EN
from maas.models import Lexeme, LexemeTranslation  # , LexemeFlexNote

LEXICON_PATH = settings.BASE_DIR / "maas" / "lexicon"


def register_translated_lexicon(path: str, lang: LanguageTag, native_lang=EN):
    with open(path) as f:
        LexemeTranslation.objects.bulk_create(
            LexemeTranslation(
                lexeme=LexemeTranslation.objects.get(
                    lang=native_lang, term=native_term
                ).lexeme,
                term=translated_term,
                lang=lang,
            )
            for native_term, translated_term in yaml.load(
                f.read(), settings.YAML_LOADER
            )
        )


def register_full_lexicon(path=LEXICON_PATH, clear=True):
    if clear:
        Lexeme.objects.all().delete()
    native_lexemes = []
    with open(os.path.join(path, "x-native.yaml")) as f:
        for native_word, flex_string in yaml.load(
            f.read(), settings.YAML_LOADER
        ).items():
            lexeme = Lexeme.objects.create()
            native_lexemes.append(
                LexemeTranslation(
                    lexeme=lexeme,
                    word=native_word,
                    lang=EN,
                )
            )
            lexeme.create_flex_notes(flex_string)
    LexemeTranslation.objects.bulk_create(native_lexemes)
    for fn in os.listdir(path):
        full_path = os.path.join(path, fn)
        if os.path.isfile(full_path) and full_path.endswith(".yaml"):
            lang_tag = fn.split(".")[0]
            if lang_tag == "x-native":
                continue
            lang, _ = LanguageTag.objects.get_or_create_from_str(lang_tag)
            register_translated_lexicon(
                full_path, lang, LanguageTag.objects.native()
            )
