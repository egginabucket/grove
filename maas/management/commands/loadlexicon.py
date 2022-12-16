import os

import yaml
from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser
from jangle.models import LanguageTag

from maas.models import Lexeme, LexemeTranslation, NativeLang


class Command(BaseCommand):
    help = "Registers Maas lexicon to database"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "-c",
            "--clear",
            action="store_true",
            help="Deletes existing data",
        )
        parser.add_argument(
            "--path",
            default=str(settings.BASE_DIR / "maas" / "lexicon"),
            help="Path to lexicon directory",
        )
        parser.add_argument(
            "--native-to-en",
            action="store_true",
            help="Also save x-maas-native translations as English",
        )

    def handle(self, *args, **options) -> None:
        if options["clear"]:
            Lexeme.objects.all().delete()  # phrases cascade
        native_lexemes = []
        path = options["path"]
        filenames = os.listdir(path)
        if "x-maas-native.yaml" in filenames:
            EN, _ = LanguageTag.objects.get_or_create_from_str("en")
            with open(os.path.join(path, "x-maas-native.yaml")) as f:
                for native_word, flex_string in yaml.load(
                    f.read(), settings.YAML_LOADER
                ).items():
                    lexeme = Lexeme.objects.create()
                    native_lexemes.append(
                        LexemeTranslation(
                            lexeme=lexeme,
                            word=native_word,
                            lang=NativeLang(),
                        )
                    )
                    if options["native_to_en"]:
                        native_lexemes.append(
                            LexemeTranslation(
                                lexeme=lexeme,
                                word=native_word,
                                lang=EN,
                            )
                        )
                        lexeme.create_flex_notes(flex_string)
            LexemeTranslation.objects.bulk_create(native_lexemes)
        for fn in filenames:
            full_path = os.path.join(path, fn)
            if os.path.isfile(full_path) and full_path.endswith(".yaml"):
                lang_tag = fn.split(".")[0]
                lang, _ = LanguageTag.objects.get_or_create_from_str(lang_tag)
                if lang == NativeLang():
                    continue
                with open(path) as f:
                    LexemeTranslation.objects.bulk_create(
                        LexemeTranslation(
                            lexeme=LexemeTranslation.objects.get(
                                lang=NativeLang(), term=native_term
                            ).lexeme,
                            term=translated_term,
                            lang=lang,
                        )
                        for native_term, translated_term in yaml.load(
                            f.read(), settings.YAML_LOADER
                        )
                    )
