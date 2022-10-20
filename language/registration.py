import os
import yaml
from django.conf import settings
from google.cloud import translate_v2 as translate
from language.models import Language, PosTag

UNIVERSAL_POS_PATH = os.path.join('language', 'universal-pos.yaml')

def get_default_translate_client():
    return translate.Client(
        target_language=settings.NATIVE_LANGUAGE_CODE,
    )

def register_languages(translate_client=get_default_translate_client(), clear=True):
    if clear:
        Language.objects.all().delete()
    Language.objects.bulk_create([Language(
            code = lang['language'],
            name = lang['name'],
        ) for lang in translate_client.get_languages(
        target_language=settings.NATIVE_LANGUAGE_CODE,
    )])

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

