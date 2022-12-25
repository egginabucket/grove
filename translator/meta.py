from typing import Generator

from jangle.models import LanguageTag

from carpet.wordnet import wordnet
from translator.models import SpacyLanguage, GoogleLanguage


def get_supported_languages() -> Generator[LanguageTag, None, None]:
    wn_langs = wordnet.langs()
    downloaded_langs = SpacyLanguage.objects.filter(downloaded=True)
    for spacy_lang in downloaded_langs.distinct("iso_lang"):
        iso_lang = spacy_lang.iso_lang
        if iso_lang.part_3 in wn_langs:
            yield LanguageTag.objects.get_from_str(iso_lang.ietf).pref_tag
