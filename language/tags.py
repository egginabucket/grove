import re
from django.db import models


ISO_639_RE = re.compile(r'[a-z]{2,3}')  # parts 1, 3, 2t, 2b
ISO_3166_1_RE = re.compile(r'[A-Z]{2}')
UN_M49_RE = re.compile(r'[0-9]{3}')
ISO_15924_RE = re.compile(r'[A-Z][a-z]{3}')

class LangTagType(models.TextChoices):
    LANG_TAG = 'L' 'language tag'
    GRANDFATHERED = 'G', 'grandfathered'
    PRIVATE_USE = 'P', 'private use'

class SubtagType(models.TextChoices):
    LANGUAGE = 'L', 'language'
    EXTLANG = 'E', 'language extension'
    REGION = 'R', 'region'
    SCRIPT = 'S', 'script'
    VARIANT = 'V', 'variant'
    

class TagType(models.TextChoices):
    """TO BE DEPRECATED
    """
    GRANDFATHERED = 'G', 'grandfathered'
    PRIVATE_USE = 'P', 'private use'
    REDUNDANT = 'X', 'redundant / irregular'
    LANGUAGE = SubtagType.LANGUAGE
    EXTLANG = SubtagType.EXTLANG
    REGION = SubtagType.REGION
    SCRIPT = SubtagType.SCRIPT
    VARIANT = SubtagType.VARIANT


def infer_tag_type(tag: str) -> SubtagType | None:
    if ISO_639_RE.fullmatch(tag):
        return TagType.LANGUAGE
    if ISO_3166_1_RE.fullmatch(tag):
        return TagType.REGION
    if UN_M49_RE.fullmatch(tag):
        return TagType.REGION
    if ISO_15924_RE.fullmatch(tag):
        return TagType.SCRIPT
    if tag.startswith('x-'):
        return TagType.PRIVATE_USE
    if tag.startswith('i-'):
        return TagType.GRANDFATHERED
