import re
from django.db import models


ISO_639_RE = re.compile(r'[a-z]{2,3}')  # parts 1, 3, 2t, 2b
ISO_3166_1_RE = re.compile(r'[A-Z]{2}')
UN_M49_RE = re.compile(r'[0-9]{3}')
ISO_15924_RE = re.compile(r'[A-Za-z]{3}')
VARIANT_DIGITS_RE = re.compile(r'\d\w{0,3}$')


class LangTagType(models.TextChoices):
    LANG_TAG = 'L' 'language tag'
    GRANDFATHERED = 'G', 'grandfathered'  # includes regular & irregular
    PRIVATE_USE = 'P', 'private use'


class SubtagType(models.TextChoices):
    LANGUAGE = 'L', 'language'
    EXTENSION = 'E', 'language extension'
    REGION = 'R', 'region'
    SCRIPT = 'S', 'script'
    VARIANT = 'V', 'variant'


class IanaSubtagType(models.TextChoices):
    LANGUAGE = SubtagType.LANGUAGE
    EXTLANG = SubtagType.EXTENSION
    REGION = SubtagType.REGION
    SCRIPT = SubtagType.SCRIPT
    VARIANT = SubtagType.VARIANT
    GRANDFATHERED = 'G', 'grandfathered / regular'
    REDUNDANT = 'X', 'redundant / irregular'


IANA_LANGUAGE_TAG_TYPES = {
    IanaSubtagType.GRANDFATHERED,
    IanaSubtagType.REDUNDANT,
}


def infer_subtag_type(tag: str):
    if ISO_639_RE.fullmatch(tag):
        return SubtagType.LANGUAGE
    if ISO_3166_1_RE.fullmatch(tag):
        return SubtagType.REGION
    if UN_M49_RE.fullmatch(tag):
        return SubtagType.REGION
    if ISO_15924_RE.fullmatch(tag):
        return SubtagType.SCRIPT

