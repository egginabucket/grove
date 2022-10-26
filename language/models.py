from functools import cached_property
from typing import Any, Optional, Sequence, Generator, Union, Type
from unittest import IsolatedAsyncioTestCase
import requests
import spacy
from spacy.language import Language
from spacy.cli.download import download_model
from spacy.cli._util import WHEEL_SUFFIX, SDIST_SUFFIX
from django.db import models
from django.conf import settings
from language import tags


class IsoLang(models.Model):
    """
    Represents an ISO 639 language.
    """
    class LangType(models.TextChoices):
        ANCIENT = 'A', 'ancient'
        CONSTRUCTED = 'C', 'constructed'
        EXTINCT = 'E', 'extinct'
        HISTORICAL = 'H', 'historical'
        LIVING = 'L', 'living'
        SPECIAL = 'S', 'special'

    class Scope(models.TextChoices):
        INDIVIDUAL = 'I', 'individual'
        MACROLANGUAGE = 'M', 'macrolanguage'
        SPECIAL = 'S', 'special'

    ref_name = models.CharField('reference name', max_length=150)
    part_3 = models.CharField(
        'alpha-3 code (ISO 639-3)', unique=True, max_length=3)
    part_1 = models.CharField(
        'alpha-2 code (ISO 639-1)', null=True, max_length=2)
    part_2b = models.CharField(
        'bibliographic code (ISO 639-2/B)', null=True, max_length=3)
    part_2t = models.CharField(
        'terminological code (ISO 639-2/T)', null=True, max_length=3)
    lang_type = models.CharField(
        'type', choices=LangType.choices, max_length=1)
    scope = models.CharField(choices=Scope.choices, max_length=1)
    comment = models.CharField(null=True, max_length=150)

    macrolanguage = models.ForeignKey(
        'self',
        related_name='individuals',
        null=True,
        on_delete=models.SET_NULL,
    )
    is_wordnet_supported = models.BooleanField(
        'supported by the Open Multilingual Wordnet', default=False)

    @staticmethod
    def kwargs_from_code(code: str, ignore_invalid=False) -> Generator[dict[str, str], None, None]:
        """Yields kwargs for querying
        from any ISO 639 code.

        Use `get_from_code` if you just need to get an object.

        Raises
        ------
        ValueError
            If `code` cannot be a valid ISO 639 code
            and ignore_invalid is not set.
        """
        if len(code) == 2:
            yield {'part_1': code}
        elif len(code) == 3:
            for field in ('part_3', 'part_2b', 'part_2t'):
                yield {field: code}
        elif not ignore_invalid:
            raise ValueError(f"cannot infer ISO 639 code from '{code}'")

    @staticmethod
    def get_from_code(code: str, **kwargs) -> Union['IsoLang', None]:
        """
        Gets an object from an ISO 639 code
        and additional query kwargs.
        """
        for iso_kwargs in IsoLang.kwargs_from_code(code):
            try:
                return IsoLang.objects.get(**iso_kwargs, **kwargs)
            except IsoLang.DoesNotExist:
                pass

    @staticmethod
    def native() -> 'IsoLang':
        return IsoLang.get_from_code(settings.NATIVE_LANG_CODE)

    @property
    def ietf(self) -> str:
        """Shortest ISO 639 code (part 1 or 3)"""
        return self.part_1 or self.part_3

    def __str__(self):
        return f"{self.part_3} - {self.ref_name}"

    class Meta:
        verbose_name = 'ISO 639 language'


class IsoLangName(models.Model):
    """Represents an English name from SIL
    for an ISO 639 language.
    """
    iso_lang = models.ForeignKey(IsoLang, related_name='names',
                                 on_delete=models.CASCADE)
    printable = models.CharField('printable translated name', max_length=75)
    inverted = models.CharField('inverted translated name', max_length=75)

    def __str__(self):
        return self.printable

    class Meta:
        verbose_name = 'language name'


class IanaSubtagRegistry(models.Model):
    """Represents a saved instance
    of the IANA Language Subtag Registry.

    See https://www.iana.org/assignments/iso_lang-subtags-templates/iso_lang-subtags-templates.xhtml,
    https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry.
    """
    file_date = models.DateField()
    saved = models.DateTimeField()

    def __str__(self):
        return f"{self.file_date} / {self.saved}"

    class Meta:
        verbose_name = 'IANA Language Subtag Registry'


class IanaSubtag(models.Model):
    """Abstract class for models
    saved from the IANA language subtag registry.
    """
    iana_registry = models.ForeignKey(
        IanaSubtagRegistry, null=True, on_delete=models.CASCADE)
    iana_deprecated = models.DateField(null=True)
    iana_added = models.DateField(null=True)
    iana_comments = models.CharField(null=True, max_length=150)
    iana_pref_value = models.CharField(max_length=12)

    def get_descriptions(self) -> list[str]:
        return [desc.text for desc in self.iana_descriptions.order_by('index')]

    def get_description(self) -> str:
        return self.iana_descriptions.order_by('index').first().text

    class Meta:
        abstract = True


class _IanaSubtagDesc(models.Model):
    """Abstract class for models
    providing descriptions for subtags
    saved from the IANA language subtag registry.
    Foreign keys to the subtag model should be defined
    with `subtag`.
    """
    index = models.PositiveSmallIntegerField(default=0)
    text = models.CharField(max_length=75)

    @staticmethod
    def _make_subtag_fk(model_cls: type) -> models.ForeignKey:
        return models.ForeignKey(model_cls, related_name='iana_descriptions', on_delete=models.CASCADE)

    def __str__(self):
        return self.text

    class Meta:
        unique_together = (('subtag', 'index'), ('subtag', 'index'))
        abstract = True


class Script(IanaSubtag):
    """Represents an ISO 15924 script.
    From https://www.unicode.org/iso15924/,
    despite being an IANA subtag.
    """
    code = models.CharField('ISO 15924 code', unique=True, max_length=4)
    no = models.PositiveSmallIntegerField('ISO 15924 number', unique=True)
    name_en = models.CharField('English name', unique=True, max_length=150)
    name_fr = models.CharField('nom français', unique=True, max_length=150)
    pva = models.CharField('property value alias', null=True, max_length=150)
    unicode_version = models.CharField(null=True, max_length=12)
    script_date = models.DateField()

    @property
    def no_str(self) -> str:
        return '{:03d}'.format(self.no)

    def __str__(self):
        return self.name_en

    class Meta:
        verbose_name = 'ISO 15924 script'


class ScriptDescription(_IanaSubtagDesc):
    subtag = _IanaSubtagDesc._make_subtag_fk(Script)


class Region(IanaSubtag):
    un_m49 = models.CharField(max_length=3)
    iso_3166 = models.CharField('alpha-2 (ISO 3166-1) code', max_length=2)


class RegionDescription(_IanaSubtagDesc):
    subtag = _IanaSubtagDesc._make_subtag_fk(Region)


class GrandfatheredLang(IanaSubtag):
    tag_text = models.TextField(max_length=12)


class GrandfatheredLangDescription(_IanaSubtagDesc):
    subtag = _IanaSubtagDesc._make_subtag_fk(GrandfatheredLang)


class LangExtension(IanaSubtag):
    text = models.CharField(max_length=3+2*(1+3))

    def __str__(self):
        return self.text

    class Meta:
        verbose_name = 'language extension'


class LangExtDescription(_IanaSubtagDesc):
    subtag = _IanaSubtagDesc._make_subtag_fk(LangExtension)


class Variant(IanaSubtag):
    """Represents an RFC 5646 variant subtag.

    See the ABNF definition at
    https://www.rfc-editor.org/rfc/rfc5646.html
    """
    text = models.CharField(max_length=5*8)
    digits = models.CharField(max_length=4)

    class Meta:
        verbose_name = 'RFC5646 variant subtag'


class VariantDescription(_IanaSubtagDesc):
    subtag = _IanaSubtagDesc._make_subtag_fk(Variant)


class Subtag(IanaSubtag):
    """Represents a BCP 47 (RFC5646) tag or subtag.

    See https://www.rfc-editor.org/info/bcp47.

    TO BE DEPRECATED...
    """
    class Scope(models.TextChoices):
        COLLECTION = 'C', 'collection'
        MACROLANGUAGE = 'M', 'macrolanguage'
        SPECIAL = 'S', 'special'
        PRIVATE_USE = 'P', 'private use'

    tag_type = models.CharField(
        'type', choices=tags.TagType.choices, max_length=1)
    tag = models.CharField(null=True, max_length=12)  # R, V
    subtag = models.CharField(null=True, max_length=12)  # not R, V
    scope = models.CharField(choices=Scope.choices,
                             null=True, max_length=1)  # L
    macrolanguage = models.CharField(
        'macrolanguage code', null=True, max_length=4)  # TODO: move to new model?
    comment = models.CharField(null=True, max_length=150)
    pref_value = models.CharField('preferred value', null=True, max_length=12)
    suppress_script = models.CharField(null=True, max_length=4)  # L

    @property
    def has_lang(self) -> bool:
        return self.tag_type in {
            tags.TagType.LANGUAGE,
            tags.TagType.EXTLANG,
            tags.TagType.VARIANT,
        }

    def get_prefixes(self) -> list[str]:
        return [prefix.text for prefix in self.prefixes.order_by('index')]

    def get_search_codes(self) -> Generator[str, None, None]:
        yield from filter(None, [self.pref_value, self.tag, self.subtag])
        yield from self.get_prefixes()

    def get_iso_macrolang(self) -> IsoLang | None:
        if not self.has_lang:
            return None
        if not self.macrolanguage:
            return None
        return IsoLang.get_from_code(self.macrolanguage, scope=IsoLang.Scope.MACROLANGUAGE)
      

    def get_iso_lang(self) -> IsoLang | None:
        if not self.has_lang:
            return None
        kwargs = dict()
        if macrolanguage := self.get_iso_macrolang():
            kwargs['macrolanguage'] = macrolanguage
        if self.scope == self.Scope.MACROLANGUAGE:
            kwargs['scope'] = IsoLang.Scope.MACROLANGUAGE
        elif self.scope == self.Scope.SPECIAL:
            kwargs['scope'] = IsoLang.Scope.SPECIAL
        elif self.scope == None:
            kwargs['scope'] = IsoLang.Scope.INDIVIDUAL

        for code in filter(tags.ISO_639_RE.fullmatch, self.get_search_codes()):
            try:
                return IsoLang.get_from_code(code, **kwargs)
            except IsoLang.DoesNotExist:
                continue

    def get_region(self) -> Any | None: return  # TODO

    def get_script(self) -> Script | None:
        for code in filter(tags.ISO_15924_RE.fullmatch, self.get_search_codes()):
            try:
                return Script.objects.get(code=code)
            except Script.DoesNotExist:
                pass

    def __str__(self):
        return f"{self.subtag or self.tag} - {self.get_tag_type_display()}"

    class Meta:
        verbose_name = 'BCP 47 language subtag'


class SubtagDescription(_IanaSubtagDesc):
    subtag = _IanaSubtagDesc._make_subtag_fk(Subtag)


class SubtagPrefix(models.Model):
    subtag = models.ForeignKey(
        Subtag, related_name='prefixes', on_delete=models.CASCADE)
    index = models.PositiveSmallIntegerField()
    text = models.CharField(max_length=150)

    def __str__(self):
        return self.text

    class Meta:
        verbose_name = 'RFC5646 language tag prefix'
        unique_together = (('subtag', 'index'), ('subtag', 'text'))


class LangTag(models.Model):
    """Represents an RFC5646 tag.

    See https://www.rfc-editor.org/rfc/rfc5646.html.
    """
    lang_type = models.CharField(choices=tags.TagType.choices, max_length=1)
    iso_lang = models.ForeignKey(
        IsoLang,
        verbose_name='language',
        null=True,
        on_delete=models.CASCADE,
    )
    script = models.ForeignKey(
        Script, null=True, on_delete=models.CASCADE)
    variants = models.ManyToManyField(Variant)
    grandfathered = models.ForeignKey(
        GrandfatheredLang, on_delete=models.CASCADE)


class GoogleLang(models.Model):
    """Information on a language regarding use with
    the Google Cloud Translate API.
    """
    iso_lang = models.ForeignKey(
        IsoLang, verbose_name='language', on_delete=models.CASCADE)
    display_name = models.CharField(max_length=75)
    supports_source = models.BooleanField()
    supports_target = models.BooleanField()
    tag = models.ForeignKey(LangTag, on_delete=models.PROTECT)

    class Meta:
        verbose_name = 'Google Cloud Translate API language'


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


def parse_spacy_model_kwargs(model_name: str, as_objs: bool) -> dict[str]:
    """Parse a SpaCy model / package name
    into kwargs for querying `SpacyLangModel`.
    """
    kwargs = dict()
    if '-' in model_name:
        components = model_name.split('-')
        model_name = "".join(components[:-1])
        kwargs['package_version'] = components[-1]

    components = model_name.split('_')

    kwargs['iso_lang'] = IsoLang.get_from_code(components.pop(0))

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


class SpacyLangModel(models.Model):
    """Represents the core metadata of a SpaCy language model.
    """
    iso_lang = models.ForeignKey(IsoLang, on_delete=models.CASCADE)
    model_type = models.ForeignKey(
        SpacyModelType, null=True, on_delete=models.PROTECT)
    genre = models.CharField(max_length=12)
    model_size = models.ForeignKey(SpacyModelSize, on_delete=models.PROTECT)
    package_version = models.CharField(max_length=126)
    downloaded = models.BooleanField(default=False)  # limit 1 to version

    @staticmethod
    def get_from_name(name: str) -> 'SpacyLangModel':
        return SpacyLangModel.objects.get(**parse_spacy_model_kwargs(name, False))

    @property
    def name(self) -> str:
        return '_'.join(filter(None, [
            self.iso_lang.short,
            self.model_type.abbr,
            self.genre,
            self.model_size.abbr
        ]))

    @property
    def full_name(self) -> str:
        return f"{self.name}-{self.package_version}"

    @cached_property
    def nlp(self) -> Language:
        return spacy.load(self.name)

    @property
    def docs_url(self) -> str:
        return f"https://spacy.io/models/{self.iso_lang.part_1}#{self.name}"

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

    class Meta:
        unique_together = ('iso_lang', 'model_type', 'genre',
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
