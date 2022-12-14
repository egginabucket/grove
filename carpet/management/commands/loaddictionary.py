from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser
from jangle.models import LanguageTag

from carpet.dictionary import DictionaryLoader
from carpet.models import Phrase


class Command(BaseCommand):
    help = "Registers dictionary linking WordNet Synsets to Carpet phrases to database"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "-c",
            "--clear",
            action="store_true",
            help="Deletes existing data",
        )
        parser.add_argument(
            "--path",
            default=str(settings.BASE_DIR / "carpet" / "dictionary"),
            help="Path to dictionary directory or file",
        )
        parser.add_argument(
            "--lang",
            default="x-maas-native",
            help="Language Maas lexemes are written in",
        )

    def handle(self, *args, **options) -> None:
        if options["clear"]:
            Phrase.objects.all().delete()  # phrases cascade
        lang = LanguageTag.objects.get_from_str(options["lang"])
        DictionaryLoader(lang).register(options["path"])
