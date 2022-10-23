from typing import Any, Generator, Iterable
from datetime import datetime
import gzip
import csv
import yaml
import requests
from requests.compat import urljoin
from requests.models import ITER_CHUNK_SIZE
from google.cloud import translate_v2 as translate
from django.conf import settings
from nltk.corpus import wordnet
from language.models import Lang, LangName, LangSubtagRegistry, LangTag, LangTagDescription, LangTagPrefix, PosTag

UNIVERSAL_POS_PATH = settings.BASE_DIR / 'language' / 'universal-pos.yaml'


def get_default_translate_client():
    return translate.Client(target_language=settings.NATIVE_LANGUAGE_CODE)


class SilTableReader(csv.DictReader):
    # https://iso639-3.sil.org/code_tables/download_tables

    base_url = 'https://iso639-3.sil.org/sites/iso639-3/files/downloads/'
    charset = 'utf-8'
    chunk_size = ITER_CHUNK_SIZE

    def __init__(self, fn: str, *args, **kwargs):
        r = requests.get(urljoin(self.base_url, fn), stream=True)
        r.raise_for_status()
        r.encoding = self.charset
        super().__init__(
            r.iter_lines(self.chunk_size, decode_unicode=True),
            dialect='excel-tab', *args, **kwargs)


class RecordJarEntry(dict[str, list[str]]):
    def add(self, key: str, val: str):
        if key in self:
            self[key].append(val)
        else:
            self[key] = [val]

    def one(self, key: str) -> str:
        vals = self[key]
        if len(vals) > 1:
            raise ValueError(f"key '{key}' has multiple values {vals}")
        if not vals:
            raise KeyError(f"key '{key}' has an empty list of values")
        return vals[0]

    def get_one(self, key: str, default=None) -> str | None | Any:
        try:
            return self.one(key)
        except KeyError:
            return default


def parse_record_jar(lines: Iterable[str], indent='\t') -> Generator[RecordJarEntry, None, None]:
    entry = RecordJarEntry()
    for line in lines:
        line_text = line.strip()
        if not line_text:
            continue
        if line.startswith(indent):
            entry[key][-1] += ' ' + line_text
        elif line_text == '%%':
            yield entry
            entry = RecordJarEntry()
        else:
            key, val = line_text.split(":", 1)
            entry.add(key.strip(), val.strip())
    yield entry


def register_macrolang_mappings(clear=True, reader=SilTableReader):
    if clear:
        Lang.objects.all().update(macrolang=None)

    mappings: dict[str, list[str]] = dict()
    last_m_id = ''
    for row in reader('iso-639-3-macrolanguages.tab'):
        if row['M_Id'] != last_m_id:
            last_m_id = row['M_Id']
            mappings[last_m_id] = []
        if row['I_Status'] == 'A':  # Active
            mappings[last_m_id].append(row['I_Id'])
    for m_part_3, i_part_3s in mappings.items():
        Lang.objects.filter(part_3__in=i_part_3s
                            ).update(macrolang=Lang.objects.get(part_3=m_part_3))


def register_lang_names(clear=True, reader=SilTableReader):
    if clear:
        LangName.objects.all().delete()

    LangName.objects.bulk_create(LangName(
        lang=Lang.objects.get(part_3=row['Id']),
        printable=row['Print_Name'],
        inverted=row['Inverted_Name'],
    ) for row in reader('iso-639-3_Name_Index.tab'))


def register_lang_tags(clear=True):
    if clear:
        LangSubtagRegistry.objects.all().delete()
    r = requests.get(
        'https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry', stream=True)
    r.raise_for_status()
    prefixes = []
    descriptions = []

    first = True
    for i, entry in enumerate(parse_record_jar(r.iter_lines(decode_unicode=True), indent='  ')):
        if first:
            registry = LangSubtagRegistry.objects.create(
                file_date=entry.one('File-Date'),
                saved=datetime.now(),
            )
            first = False
            continue
        tag = LangTag.objects.create(
            registry=registry,
            tag_type=getattr(LangTag.TagType, entry.one('Type').upper()),
            deprecated=entry.get_one('Deprecated'),
            added=entry.one('Added'),
            subtag=entry.get_one('Subtag'),
            tag=entry.get_one('Tag'),
            scope=getattr(LangTag.Scope, entry.one(
                'Scope').upper().replace('-', '_')) if 'Scope' in entry else None,
            comment=entry.get_one('Comments'),
            pref_value=entry.get_one('Preferred-Value'),
            suppress_script=entry.get_one('Suppress-Script'),
        )
        prefixes.extend(LangTagPrefix(
            tag=tag,
            index=j,
            text=text,
        ) for j, text in enumerate(entry.get('Prefix', [])))
        descriptions.extend(LangTagDescription(
            tag=tag,
            index=j,
            text=text,
        ) for j, text in enumerate(entry.get('Description', [])))
        if not i % 32:
            LangTagPrefix.objects.bulk_create(prefixes)
            prefixes = []
            LangTagDescription.objects.bulk_create(descriptions)
            descriptions = []

    LangTagPrefix.objects.bulk_create(prefixes)
    LangTagDescription.objects.bulk_create(descriptions)


def register_langs(clear=True, sil_table_reader=SilTableReader, translate_client=get_default_translate_client):
    if clear:
        Lang.objects.all().delete()

    wn_langs = wordnet.langs()
    Lang.objects.bulk_create(Lang(
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

    register_macrolang_mappings(False, sil_table_reader)
    register_lang_names(False, sil_table_reader)
    register_lang_tags(clear)

    """
    Lang.objects.bulk_create([Lang(
            code = lang['language'],
            name = lang['name'],
        ) for lang in translate_client.get_languages(
        target_language=settings.NATIVE_LANGUAGE_CODE,
    )])
    """


def register_pos_tags(path=UNIVERSAL_POS_PATH, clear=True):
    if clear:
        PosTag.objects.all().delete()
    with open(path) as f:
        pos_tags = []
        for cat, tags in yaml.load(f.read(), settings.YAML_LOADER).items():
            for abbr, name in tags.items():
                pos_tags.append(PosTag(abbr=abbr, name=name, category=cat))
        PosTag.objects.bulk_create(pos_tags)
