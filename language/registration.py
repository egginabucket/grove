from datetime import datetime
from typing import Optional
# import gzip
import csv
import yaml
import requests
from requests.compat import urljoin
from requests.models import ITER_CHUNK_SIZE
from google.cloud import translate
from django.conf import settings
from nltk.corpus import wordnet
from language import models, tags
from language.record_jar import parse_record_jar
"""
from language.models import (
    models.IsoLang, models.IsoLangName, LangSubtagRegistry, models.LangTag,
    models.LangTagDescription, models.LangTagPrefix, models.PosTag, models.Script
)"""

UNIVERSAL_POS_PATH = settings.BASE_DIR / 'language' / 'universal-pos.yaml'


def get_default_translate_client():
    return translate.TranslationServiceClient(target_language=models.IsoLang.native().part_1)


class SilTableReader(csv.DictReader):
    """Inherits from `csv.DictReader` to read tab-delimited data
    from https://iso639-3.sil.org/sites/iso639-3/files/downloads/.

    More information is available at
    https://iso639-3.sil.org/code_tables/download_tables
    """
    base_url = 'https://iso639-3.sil.org/sites/iso639-3/files/downloads/'
    chunk_size = ITER_CHUNK_SIZE

    def __init__(self, fn: str, *args, **kwargs):
        r = requests.get(urljoin(self.base_url, fn), stream=True)
        r.raise_for_status()
        r.encoding = 'utf-8'
        super().__init__(
            r.iter_lines(self.chunk_size, decode_unicode=True),
            dialect='excel-tab', *args, **kwargs)


def register_scripts(clear=True):
    """Saves IS0 15924 scripts from unicode.org to the database.
    See https://www.unicode.org/iso15924/iso15924.txt.
    """
    if clear:
        models.Script.objects.all().delete()

    r = requests.get('https://www.unicode.org/iso15924/iso15924.txt')
    r.raise_for_status()

    def line_is_valid(line: str) -> bool:
        line = line.strip()
        return bool(line and not line.startswith('#'))

    models.Script.objects.bulk_create(models.Script(
        **{key: val or None for key, val in row.items()},
    ) for row in csv.DictReader(
        filter(line_is_valid, r.iter_lines(decode_unicode=True)),
        ['code', 'no', 'name_en',
         'name_fr', 'pva', 'unicode_version', 'script_date'],
        delimiter=';'
    ))


def register_macrolanguage_mappings(clear=True, reader=SilTableReader):
    """Saves IS0 639-3 macrolanguage mappings from sil.org to the database.
    """
    if clear:
        models.IsoLang.objects.all().update(macrolanguage=None)

    mappings: dict[str, list[str]] = dict()
    last_m_id = ''
    for row in reader('iso-639-3-macrolanguages.tab'):
        if row['M_Id'] != last_m_id:
            last_m_id = row['M_Id']
            mappings[last_m_id] = []
        if row['I_Status'] == 'A':  # Active
            mappings[last_m_id].append(row['I_Id'])
    for m_part_3, i_part_3s in mappings.items():
        models.IsoLang.objects.filter(part_3__in=i_part_3s
                                   ).update(macrolanguage=models.IsoLang.objects.get(part_3=m_part_3))


def register_lang_names(clear=True, reader=SilTableReader):
    """Saves ISO 639 language names from sil.org to the database.
    See https://iso639-3.sil.org/sites/iso639-3/files/downloads/iso-639-3_Name_Index.tab.
    """
    if clear:
        models.IsoLangName.objects.all().delete()

    models.IsoLangName.objects.bulk_create(models.IsoLangName(
        iso_lang=models.IsoLang.objects.get(part_3=row['Id']),
        printable=row['Print_Name'],
        inverted=row['Inverted_Name'],
    ) for row in reader('iso-639-3_Name_Index.tab'))


def register_iana_subtags(clear=True):
    """Saves BCP 47 tags from the IANA language subtag registry to the database.
    """
    if clear:
        models.IanaSubtagRegistry.objects.all().delete()
    r = requests.get(
        'https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry', stream=True)
    r.raise_for_status()
    prefixes = []
    descriptions = []

    first = True
    for i, entry in enumerate(parse_record_jar(r.iter_lines(decode_unicode=True), indent='  ')):
        if first:
            registry = models.IanaSubtagRegistry.objects.create(
                file_date=entry.one('File-Date'),
                saved=datetime.now(),
            )
            first = False
            continue
        subtag = models.Subtag.objects.create(
            iana_registry=registry,
            tag_type=getattr(tags.TagType, entry.one('Type').upper()),
            iana_deprecated=entry.get_one('Deprecated'),
            iana_added=entry.one('Added'),
            subtag=entry.get_one('Subtag'),
            tag=entry.get_one('Tag'),
            scope=getattr(models.Subtag.Scope, entry.one(
                'Scope').upper().replace('-', '_')) if 'Scope' in entry else None,
            comment=entry.get_one('Comments'),
            pref_value=entry.get_one('Preferred-Value'),
            suppress_script=entry.get_one('Suppress-models.Script'),
        )
        prefixes.extend(models.SubtagPrefix(
            subtag=subtag,
            index=j,
            text=text,
        ) for j, text in enumerate(entry.get('Prefix', [])))
        descriptions.extend(models.SubtagDescription(
            subtag=subtag,
            index=j,
            text=text,
        ) for j, text in enumerate(entry.get('Description', [])))
        if not i % 32:
            models.SubtagPrefix.objects.bulk_create(prefixes)
            prefixes = []
            models.SubtagDescription.objects.bulk_create(descriptions)
            descriptions = []

    models.SubtagPrefix.objects.bulk_create(prefixes)
    models.SubtagDescription.objects.bulk_create(descriptions)


def register_google_langs(clear=True, client: Optional[translate.TranslationServiceClient] = None, location='global'):
    if clear:
        models.GoogleLang.objects.all().delete()
    if not client:
        client = get_default_translate_client()
    parent = f"projects/{settings.GOOGLE_CLOUD_PROJECT_ID}/locations/{location}"
    resp = client.get_supported_languages(
        display_language_code=models.IsoLang.short, parent=parent)
    langs = []
    for iso_lang in resp.languages:
        langs.append(models.GoogleLang(
            supports_source=iso_lang.support_source,
            supports_target=iso_lang.support_target,
        ))

    models.GoogleLang.objects.bulk_create(models.GoogleLang(
        iso_lang=models.IsoLang.get_from_code(iso_lang.language_code),
        display_name=iso_lang.display_name,

        # subtag TODO
    ) for iso_lang in resp.languages)


def register_langs(clear=True, sil_table_reader=SilTableReader,
                   translate_client: Optional[translate.TranslationServiceClient] = None):
    """Saves languages from sil.org,
    language tags,
    and Google Cloud information.
    """
    if clear:
        models.IsoLang.objects.all().delete()

    wn_langs = wordnet.langs()
    models.IsoLang.objects.bulk_create(models.IsoLang(
        part_3=row['Id'],
        part_2b=row['Part2B'] or None,
        part_2t=row['Part2T'] or None,
        part_1=row['Part1'] or None,
        scope=row['Scope'],
        lang_type=row['Language_Type'],
        ref_name=row['Ref_Name'],
        comment=row['Comment'] or None,
        is_wordnet_supported=row['Id'] in wn_langs,
    ) for row in sil_table_reader('iso-639-3.tab'))

    register_macrolanguage_mappings(False, sil_table_reader)
    register_lang_names(False, sil_table_reader)
    register_scripts(clear)
    register_iana_subtags(clear)

    """
    models.IsoLang.objects.bulk_create([models.IsoLang(
            code = iso_lang['language'],
            name = iso_lang['name'],
        ) for iso_lang in translate_client.get_languages(
        target_language=models.IsoLang.native().part_1,
    )])
    """


def register_pos_tags(path=UNIVERSAL_POS_PATH, clear=True):
    if clear:
        models.PosTag.objects.all().delete()
    with open(path) as f:
        pos_tags = []
        for cat, tags in yaml.load(f.read(), settings.YAML_LOADER).items():
            for abbr, name in tags.items():
                pos_tags.append(models.PosTag(
                    abbr=abbr, name=name, category=cat))
        models.PosTag.objects.bulk_create(pos_tags)
