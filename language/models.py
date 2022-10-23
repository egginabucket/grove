from functools import cached_property
from typing import Any, Sequence, Generator
import requests
import spacy
from spacy.language import Language
from spacy.cli.download import download_model
from spacy.cli._util import WHEEL_SUFFIX, SDIST_SUFFIX
from django.conf import settings
from django.db import models


def parse_google_lang_kwargs(tachy: str) -> dict[str]:
    kwargs = dict()
    tokens = tachy.split('/')
    lang = tachy[0]
    if len(lang) == 2:
        tokens['iso_639_1'] = lang
    elif len(lang) == 3:
        tokens['iso_639_2t'] = lang
    else:
        raise ValueError(f"invalid ISO code in {tachy}")
    if len(tokens) > 1:
        kwargs['country_code'] = tokens[1]


"""
class Lang(models.Model):
    name = models.CharField(
        verbose_name='translated display name', max_length=126)

    @staticmethod
    def native() -> 'Lang':
        return Lang.objects.get(code=settings.NATIVE_LANGUAGE_CODE)

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ('code_639_2t', 'country_code')

class LangIsoDefinition(models.Model):
    language = models.ForeignKey(
        Lang, related_name='iso_definitions', on_delete=models.CASCADE)
    code = models.CharField(
        verbose_name='ISO 639-1 code', max_length=2, null=True)
    code_2t = models.CharField(verboise_name='ISO 639-2/t code', max_length=3)
    country_code = models.CharField(
        verbose_name='ideally ISO 3166-1 alpha 2 code', max_length=12)
"""

# https://iso639-3.sil.org/code_tables/download_tables


def iso_639_kwargs(code: str, ignore_invalid=False) -> Generator[dict[str, str], None, None]:
    if len(code) == 2:
        yield {'part_1': code}
    elif len(code) == 3:
        for field in ('part_3', 'part_2b', 'part_2t'):
            yield {field: code}
    elif not ignore_invalid:
        raise ValueError(f"cannot infer ISO 639 code from '{code}'")


class Lang(models.Model):
    class Scope(models.TextChoices):
        INDIVIDUAL = 'I', 'individual'
        MACROLANG = 'M', 'macrolanguage'
        SPECIAL = 'S', 'special'

    class LangType(models.TextChoices):
        ANCIENT = 'A', 'ancient'
        CONSTRUCTED = 'C', 'constructed'
        EXTINCT = 'E', 'extinct'
        HISTORICAL = 'H', 'historical'
        LIVING = 'L', 'living'
        SPECIAL = 'S', 'special'

    part_3 = models.CharField(
        'alpha-3 code (ISO 639-3)', unique=True, max_length=3)
    part_1 = models.CharField(
        'alpha-2 code (ISO 639-1)', null=True, max_length=2)
    part_2b = models.CharField(
        'bibliographic code (ISO 639-2/B)', null=True, max_length=3)
    part_2t = models.CharField(
        'terminological code (ISO 639-2/T)', null=True, max_length=3)

    scope = models.CharField(choices=Scope.choices, max_length=1)
    lang_type = models.CharField(
        'type', choices=LangType.choices, max_length=1)
    ref_name = models.CharField(max_length=150)
    comment = models.CharField(null=True, max_length=150)

    macrolang = models.ForeignKey(
        'self',
        verbose_name='macrolanguage',
        related_name='individuals',
        null=True,
        on_delete=models.SET_NULL,
    )
    is_wordnet_supported = models.BooleanField(
        'supported by the Open Multilingual Wordnet', default=False)

    def __str__(self):
        return f"{self.part_3} - {self.ref_name}"

    class Meta:
        verbose_name = 'ISO 639 language'


class LangName(models.Model):
    lang = models.ForeignKey(Lang, related_name='names',
                             on_delete=models.CASCADE)
    printable = models.CharField('printable translated name', max_length=75)
    inverted = models.CharField('inverted translated name', max_length=75)

    def __str__(self):
        return self.printable

    class Meta:
        verbose_name = 'language name'


class LangSubtagRegistry(models.Model):
    file_date = models.DateField()
    saved = models.DateTimeField()

    def __str__(self):
        return f"{self.file_date} / {self.saved}"

    class Meta:
        verbose_name = 'IANA Language Subtag Registry'


class LangTag(models.Model):
    class TagType(models.TextChoices):
        LANGUAGE = 'L', 'language'
        EXTLANG = 'E', 'external language'
        REGION = 'R', 'region'
        SCRIPT = 'S', 'script'
        VARIANT = 'V', 'variant'
        GRANDFATHERED = 'G', 'grandfathered'
        REDUNDANT = 'X', 'redundant'
        PRIVATE_USE = 'P', 'private use'

    class Scope(models.TextChoices):
        COLLECTION = 'C', 'collection'
        MACROLANGUAGE = 'M', 'macrolanguage'
        SPECIAL = 'S', 'special'
        PRIVATE_USE = 'P', 'private use'

    registry = models.ForeignKey(
        LangSubtagRegistry, related_name='subtags', on_delete=models.CASCADE)

    tag_type = models.CharField('type', choices=TagType.choices, max_length=1)
    tag = models.CharField(null=True, max_length=12)  # R, V
    subtag = models.CharField(null=True, max_length=12)  # not R, V
    deprecated = models.DateField('date deprecated', null=True)
    added = models.DateField('date added')
    scope = models.CharField(choices=Scope.choices,
                             null=True, max_length=1)  # L
    macrolang = models.CharField('macrolanguage code', null=True, max_length=4)
    comment = models.CharField(null=True, max_length=150)
    pref_value = models.CharField('preferred value', null=True, max_length=12)
    suppress_script = models.CharField(null=True, max_length=4)  # L

    @property
    def has_lang(self) -> bool:
        return self.tag_type in {
            self.TagType.LANGUAGE,
            self.TagType.EXTLANG,
            self.TagType.VARIANT,
        }

    def get_prefixes(self) -> list[str]:
        return [prefix.text for prefix in self.prefixes.order_by('index')]

    def get_descriptions(self) -> list[str]:
        return [desc.text for desc in self.descriptions.order_by('index')]

    def get_iso_639_macrolang(self) -> Lang | None:
        if not self.has_lang:
            return None
        if not self.macrolang:
            return None
        for kwargs in iso_639_kwargs(self.macrolang, True):
            try:
                return Lang.objects.get(
                    scope=Lang.Scope.MACROLANG,
                    **kwargs,
                )
            except Lang.DoesNotExist:
                pass

    def get_iso_639(self) -> Lang:
        if not self.has_lang:
            return None
        kwargs = dict()
        if macrolang := self.get_iso_639_macrolang():
            kwargs['macrolang'] = macrolang
        if self.scope == self.Scope.MACROLANGUAGE:
            kwargs['scope'] = Lang.Scope.MACROLANG
        elif self.scope == self.Scope.SPECIAL:
            kwargs['scope'] = Lang.Scope.SPECIAL
        elif self.scope == None:
            kwargs['scope'] = Lang.Scope.INDIVIDUAL

        for code in [self.pref_value, self.tag,
                     self.subtag, *self.get_prefixes()]:
            if not code:
                continue
            for iso_kwargs in iso_639_kwargs(code, True):
                try:
                    return Lang.objects.get(
                        **kwargs,
                        **iso_kwargs,
                    )
                except Lang.DoesNotExist:
                    pass

    def __str__(self):
        return f"{self.subtag or self.tag} - {self.get_tag_type_display()}"

    class Meta:
        verbose_name = 'RFC5646 language tag'


class LangTagDescription(models.Model):
    tag = models.ForeignKey(
        LangTag, related_name='descriptions', on_delete=models.CASCADE)
    index = models.PositiveSmallIntegerField()
    text = models.CharField(max_length=150)

    def __str__(self):
        return self.text

    class Meta:
        verbose_name = 'RFC5646 language tag description'
        unique_together = (('tag', 'index'), ('tag', 'text'))


class LangTagPrefix(models.Model):
    tag = models.ForeignKey(
        LangTag, related_name='prefixes', on_delete=models.CASCADE)
    index = models.PositiveSmallIntegerField()
    text = models.CharField(max_length=150)

    def __str__(self):
        return self.text

    class Meta:
        verbose_name = 'RFC5646 language tag prefix'
        unique_together = (('tag', 'index'), ('tag', 'text'))


"""
class ExtLang(models.Model):


class LangTagExt(models.Model):
    code = models.CharField()

class LangTagVariant(models.Model):
"""

"""
class MacroLang(models.Model):
    m = models.ForeignKey(Lang, verbose_name='macrolanguage',
                          related_name='individuals', on_delete=models.CASCADE)
    i = models.ForeignKey(Lang, verbose_name='individual language',
                          related_name='macros', on_delete=models.CASCADE)
    active = models.BooleanField(default=True)

    @property
    def i_status(self) -> str:
        return 'A' if self.active else 'R'

    @property.setter
    def i_status(self, val: str):
        if val == 'A':
            self.active = True
        elif val == 'R':
            self.active = False
        else:
            raise ValueError(f"invalid status {val}")

    def __str__(self):
        return f"{self.m.iso_639_3}/{self.i.iso_639_}"
"""


class SpacyModelSize(models.Model):
    abbr = models.CharField('abbreviation', max_length=12, unique=True)
    scale = models.PositiveSmallIntegerField(
        'small-to-large scale', unique=True)
    name = models.CharField(max_length=126, unique=True)

    def __str__(self):
        return self.name


class SpacyModelType(models.Model):
    abbr = models.CharField('abbreviation', max_length=12, unique=True)

    def __str__(self):
        return self.abbr


def parse_to_spacy_model_kwargs(model_name: str, as_objs: bool) -> dict[str]:
    kwargs = dict()
    if '-' in model_name:
        components = model_name.split('-')
        model_name = "".join(components[:-1])
        kwargs['package_version'] = components[-1]

    components = model_name.split('_')
    kwargs['lang__part_1'] = components.pop(0)
    kwargs['model_size__abbr'] = components.pop(-1)
    kwargs['genre'] = components.pop(-1)
    if len(components):
        kwargs['model_type__abbr'] = components.pop(0)
    if len(components):
        raise ValueError(
            f"could not resolve model name '{model_name}' with extra componnts {components}")
    if as_objs:
        kwargs['lang'] = Lang.objects.get(part_1=kwargs.pop('lang__part_1'))
        kwargs['model_size'] = SpacyModelSize.objects.get(
            abbr=kwargs.pop('model_size__abbr'))
        if 'model_type__abbr' in kwargs:
            kwargs['model_type'] = SpacyModelType.objects.get(
                abbr=kwargs.pop('model_type__abbr'))
    return kwargs


class SpacyLangModel(models.Model):
    lang = models.ForeignKey(Lang, on_delete=models.CASCADE)
    model_type = models.ForeignKey(
        SpacyModelType, null=True, on_delete=models.PROTECT)
    genre = models.CharField(max_length=12)
    model_size = models.ForeignKey(SpacyModelSize, on_delete=models.PROTECT)
    package_version = models.CharField(max_length=126)
    downloaded = models.BooleanField(default=False)  # limit 1 to version

    @staticmethod
    def get_from_name(name: str) -> 'SpacyLangModel':
        return SpacyLangModel.objects.get(**parse_to_spacy_model_kwargs(name, False))

    @cached_property
    def name(self) -> str:
        name_components = [self.lang.part_1, self.genre, self.model_size.abbr]
        if self.model_type:
            name_components.insert(1, self.model_type.abbr)
        return '_'.join(name_components)

    @cached_property
    def full_name(self) -> str:
        return f"{self.name}-{self.package_version}"

    @cached_property
    def nlp(self) -> Language:
        return spacy.load(self.name)

    @cached_property
    def docs_url(self) -> str:
        return f"https://spacy.io/models/{self.lang.part_1}#{self.name}"

    @cached_property
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

    class Meta:
        unique_together = ('lang', 'model_type', 'genre',
                           'model_size', 'package_version')


# https://universaldependencies.org/u/pos/
# used in spacy, 'universal' tagset in nltk
class PosTag(models.Model):
    class Category(models.TextChoices):
        OPEN_CLASS = 'O', 'open class'
        CLOSED_CLASS = 'C', 'closed class'
        OTHER = 'X', 'other'

    abbr = models.CharField('abbreviation', max_length=5)
    name = models.CharField(max_length=126)
    category = models.CharField(choices=Category.choices, max_length=1)

    def __save__(self, *args, **kwargs):
        self.abbr = self.abbr.upper()
        self.description = self.description.lower()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.abbr

    class Meta:
        verbose_name = 'universal POS tag'
