from functools import cached_property
from typing import Any, Sequence
import requests
import spacy
from spacy.language import Language as Language_
from spacy.cli.download import download_model
from spacy.cli._util import WHEEL_SUFFIX, SDIST_SUFFIX
from django.conf import settings
from django.db import models

class Language(models.Model):
    code = models.CharField(max_length=126, unique=True)
    name = models.CharField(verbose_name='translated display name', max_length=126)

    @staticmethod
    def native() -> 'Language':
        return Language.objects.get(code=settings.NATIVE_LANGUAGE_CODE)

    def __str__(self):
        return self.name


class SpacyModelSize(models.Model):
    abbr = models.CharField(verbose_name='abbreviation', max_length=12, unique=True)
    scale = models.PositiveSmallIntegerField(verbose_name='small-to-large scale', unique=True)
    name = models.CharField(max_length=126, unique=True)

    def __str__(self):
        return self.name

class SpacyModelType(models.Model):
    abbr = models.CharField(verbose_name='abbreviation', max_length=12, unique=True)

    def __str__(self):
        return self.abbr

def parse_to_spacy_model_kwargs(model_name: str, as_objs: bool) -> dict[str]:
    kwargs = dict()
    if '-' in model_name:
        components = model_name.split('-')
        model_name = "".join(components[:-1])
        kwargs['package_version'] = components[-1]
    
    components = model_name.split('_')
    kwargs['language__code'] = components.pop(0)
    kwargs['model_size__abbr'] = components.pop(-1)
    kwargs['genre'] = components.pop(-1)
    if len(components):
        kwargs['model_type__abbr'] = components.pop(0)
    if len(components):
        raise ValueError(f"could not resolve model name '{model_name}' with extra componnts {components}")
    if as_objs:
        kwargs['language'] = Language.objects.get(code=kwargs.pop('language__code'))
        kwargs['model_size'] = SpacyModelSize.objects.get(abbr=kwargs.pop('model_size__abbr'))
        if 'model_type__abbr' in kwargs:
            kwargs['model_type'] = SpacyModelType.objects.get(abbr=kwargs.pop('model_type__abbr'))
    return kwargs

class SpacyLanguageModel(models.Model):
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    model_type = models.ForeignKey(SpacyModelType, null=True, on_delete=models.PROTECT)
    genre = models.CharField(max_length=12)
    model_size = models.ForeignKey(SpacyModelSize, on_delete=models.PROTECT)
    package_version = models.CharField(max_length=126)
    downloaded = models.BooleanField(default=False) # limit 1 to version

    @staticmethod
    def get_from_name(name: str) -> 'SpacyLanguageModel':
        return SpacyLanguageModel.objects.get(**parse_to_spacy_model_kwargs(name, False))

    @cached_property
    def name(self) -> str:
        name_components = [self.language.code, self.genre, self.model_size.abbr]
        if self.model_type:
            name_components.insert(1, self.model_type.abbr)
        return '_'.join(name_components)
    
    @cached_property
    def full_name(self) -> str:
        return  f"{self.name}-{self.package_version}"
    
    @cached_property
    def nlp(self) -> Language_:
        return spacy.load(self.name)
    
    def download(self, sdist=False, *user_pip_args: Sequence[str]):
        download_model("{m}-{v}/{m}-{v}{s}#egg={m}=={v}".format(
            m = self.name,
            v = self.package_version,
            s = SDIST_SUFFIX if sdist else WHEEL_SUFFIX,
        ), *user_pip_args)
        self.downloaded = True
        self.save()
    
    def get_github_meta(self) -> Any:
        return requests.get(f"https://raw.githubusercontent.com/explosion/spacy-models/master/meta/{self.full_name}.json").json()
    
    def __str__(self):
        return self.full_name
    
    class Meta:
        unique_together = ('language', 'model_type', 'genre', 'model_size', 'package_version')
        

# https://universaldependencies.org/u/pos/
# used in spacy, 'universal' tagset in nltk
class PosTag(models.Model):
    class Category(models.IntegerChoices):
        OPEN_CLASS = 0, 'open class'
        CLOSED_CLASS = 1, 'closed class'
        OTHER = 2, 'other'

    abbr = models.CharField(verbose_name='abbreviation', max_length=5)
    name = models.CharField(max_length=126)
    category = models.SmallIntegerField(choices=Category.choices)

    def __save__(self, *args, **kwargs):
        self.abbr = self.abbr.upper()
        self.description = self.description.lower()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.abbr
    
    class Meta:
        verbose_name = 'universal POS tag'
