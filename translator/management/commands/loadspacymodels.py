import os

import yaml
from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser
from spacy.cli.download import get_compatibility, get_version

from translator.models import SpacyLanguage, parse_spacy_model_kwargs


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("file")
        parser.add_argument(
            "-c",
            "--clear",
            action="store_true",
            help="Deletes existing data",
        )
        parser.add_argument(
            "-d",
            "--download",
            action="store_true",
            help="Download models",
        )
        parser.add_argument(
            "--dir",
            default=str(settings.BASE_DIR / "translator" / "spacy-models"),
            help="Deletes existing data",
        )

    def handle(self, *args, **options) -> None:
        if options["clear"]:
            SpacyLanguage.objects.all().delete()
        compat = get_compatibility()
        with open(
            os.path.join(options["dir"], (options["file"] + ".yaml"))
        ) as f:
            model_names = yaml.load(f.read(), settings.YAML_LOADER).keys()
            langs = SpacyLanguage.objects.bulk_create(
                SpacyLanguage(
                    package_version=get_version(model_name, compat),
                    **parse_spacy_model_kwargs(model_name, True)
                )
                for model_name in model_names
            )
            if options["download"]:
                for lang in langs:
                    lang.download()
