from __future__ import annotations

from typing import Any, Optional, Sequence

import requests
from django.conf import settings
from django.db import models
from google.cloud import translate
from jangle.models import ISOLanguage, LanguageTag
from jangle.utils import BatchedCreateManager
from spacy.cli._util import SDIST_SUFFIX, WHEEL_SUFFIX
from spacy.cli.download import download_model


class GoogleLanguageManager(BatchedCreateManager['GoogleLanguage']):
    def register(self, clear=True, batch_size=64, client: Optional[translate.TranslationServiceClient] = None, location='global'):
        if clear:
            self.all().delete()
        if not client:
            client = translate.TranslationServiceClient()
        parent = f"projects/{settings.GOOGLE_CLOUD_PROJECT_ID}/locations/{location}"
        resp = client.get_supported_languages(
            display_language_code=str(LanguageTag.objects.native()), parent=parent)
        self.batched_create((self.model(
            lang=LanguageTag.objects.get_or_create_from_str(
                lang.language_code),
            display_name=lang.display_name,
            supports_source=lang.support_source,
            supports_target=lang.support_target,
        ) for lang in resp.languages), batch_size)  # type: ignore


class GoogleLanguage(models.Model):
    """Information on a language regarding use with
    the Google Cloud Translate API.
    """
    language_tag = models.ForeignKey(LanguageTag, on_delete=models.CASCADE)
    display_name = models.CharField(max_length=75)
    supports_source = models.BooleanField()
    supports_target = models.BooleanField()

    objects = BatchedCreateManager()

    class Meta:
        verbose_name = 'Google Cloud Translate API language'


class SpacyModelSize(models.Model):
    abbr = models.CharField('abbreviation', max_length=12, unique=True)
    scale = models.PositiveSmallIntegerField(
        'small-to-large scale', unique=True)
    name = models.CharField(max_length=126, unique=True)

    def __str__(self):
        return self.abbr


class SpacyModelType(models.Model):
    abbr = models.CharField('abbreviation', max_length=12, unique=True)

    def __str__(self):
        return self.abbr


def parse_spacy_model_kwargs(model_name: str, as_objs: bool) -> dict[str, Any]:
    """Parse a SpaCy model / package name
    into kwargs for querying `SpacyLangModel`.
    """
    kwargs = dict()
    if '-' in model_name:
        components = model_name.split('-')
        model_name = "".join(components[:-1])
        kwargs['package_version'] = components[-1]

    components = model_name.split('_')

    kwargs['iso_lang'] = ISOLanguage.objects.get_from_ietf(
        components.pop(0))

    kwargs['model_size__abbr'] = components.pop(-1)
    kwargs['genre'] = components.pop(-1)
    if len(components):
        kwargs['model_type__abbr'] = components.pop(0)
    if len(components):
        raise ValueError(
            f"could not resolve model name '{model_name}' with extra componnts {components}")
    if as_objs:
        kwargs['model_size'] = SpacyModelSize.objects.get(
            abbr=kwargs.pop('model_size__abbr'))
        if 'model_type__abbr' in kwargs:
            kwargs['model_type'] = SpacyModelType.objects.get(
                abbr=kwargs.pop('model_type__abbr'))
    return kwargs


class SpacyLanguageQuerySet(models.QuerySet['SpacyLanguage']):
    def get_from_name(self, name: str) -> SpacyLanguageQuerySet:
        return self.filter(**parse_spacy_model_kwargs(name, False))

    def from_lang(self, lang: LanguageTag) -> SpacyLanguageQuerySet:
        if not (lang.lang and lang.lang.iso_lang):
            raise ValueError(f"Language-Tag {lang} not defined ISO 639")
        return self.filter(iso_lang=lang.lang.iso_lang)

    def largest(self) -> Optional[SpacyLanguage]:
        return self.order_by('-model_size__scale').first()


class SpacyLanguageManager(models.Manager['SpacyLanguage']):
    def get_queryset(self) -> SpacyLanguageQuerySet:
        return SpacyLanguageQuerySet(self.model, using=self._db)

    def get_from_name(self, name: str) -> SpacyLanguageQuerySet:
        return self.get_queryset().get_from_name(name)

    def from_lang(self, lang: LanguageTag) -> SpacyLanguageQuerySet:
        return self.get_queryset().from_lang(lang)

    def largest(self) -> Optional[SpacyLanguage]:
        return self.get_queryset().largest()


class SpacyLanguage(models.Model):
    """Represents the core metadata of a SpaCy language model.
    """
    iso_lang = models.ForeignKey(ISOLanguage, on_delete=models.CASCADE)
    model_type = models.ForeignKey(
        SpacyModelType, null=True, on_delete=models.PROTECT)
    genre = models.CharField(max_length=12)
    model_size = models.ForeignKey(SpacyModelSize, on_delete=models.PROTECT)
    package_version = models.CharField(max_length=126)
    downloaded = models.BooleanField(default=False)  # limit 1 to version

    @property
    def name(self) -> str:
        return '_'.join(filter(None, [
            self.iso_lang.ietf,
            self.model_type and self.model_type.abbr,
            self.genre,
            self.model_size.abbr
        ]))

    @property
    def full_name(self) -> str:
        return f"{self.name}-{self.package_version}"

    @property
    def docs_url(self) -> str:
        return f"https://spacy.io/models/{self.iso_lang.ietf}#{self.name}"

    @property
    def github_meta_url(self) -> str:
        return f"https://raw.githubusercontent.com/explosion/spacy-models/master/meta/{self.full_name}.json"

    def download(self, sdist=False, *user_pip_args: Sequence[str]):
        download_model("{m}-{v}/{m}-{v}{s}#egg={m}=={v}".format(
            m=self.name,
            v=self.package_version,
            s=SDIST_SUFFIX if sdist else WHEEL_SUFFIX,
        ), *user_pip_args)
        self.downloaded = True
        self.save()

    def get_github_meta(self) -> Any:
        return requests.get(self.github_meta_url).json()

    def __str__(self):
        return self.full_name

    objects = SpacyLanguageManager()

    class Meta:
        unique_together = (
            'iso_lang', 'model_type', 'genre',
            'model_size', 'package_version')
