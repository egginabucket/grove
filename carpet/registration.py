import os
import yaml
from django.db.utils import IntegrityError
from django.conf import settings
from language.models import SpacyLangModel
from carpet.base import AbstractPhrase, Depth
from carpet.models import Phrase, PhraseComposition, Term, parse_term_kwargs
from carpet.parser import StrPhrase
from maas.models import LexemeTranslation

def register_phrase(phrase: AbstractPhrase) -> Phrase:
    # recursive, lexemes not supported
    if isinstance(phrase, Phrase):
        return phrase
    obj = Phrase.objects.create(
        pitch_change = phrase.pitch_change,
        multiplier = phrase.multiplier,
        suffix = phrase.suffix,
        count = phrase.count,
        lexeme = getattr(phrase, 'lexeme', None),
    )
    for i, child in enumerate(phrase.children):
        PhraseComposition.objects.create(
            parent = obj,
            child = register_phrase(child),
            index = i,
            has_braces = phrase.has_braces,
        )
    return obj


def register_dictionary(path: str, lang_m: SpacyLangModel):
    for subpath in sorted(os.listdir(path)):
        full_path = os.path.join(path, subpath)
        if os.path.isdir(full_path):
            register_dictionary(full_path, lang_m)
        elif os.path.isfile(full_path) and full_path.endswith('.yaml'):
            with open(full_path) as f:
                if subpath.split('.')[0] == '0-lexical-synonyms':
                    # terms = []
                    for lexeme_word, tachys in yaml.load(f.read(), settings.YAML_LOADER).items():
                        try:
                            lexeme = LexemeTranslation.objects.get(word=lexeme_word, iso_lang=lang_m.iso_lang,).lexeme
                        except Exception as e:
                            raise ValueError(f"lexeme '{lexeme_word}' from '{full_path}' raised {e}")
                        #phrase = apply_model_phrase(iso_lang, Phrase.objects.create(lexeme=lexeme))
                        phrase, _  = Phrase.objects.get_or_create(lexeme=lexeme)
                        for tachy in tachys:
                            term = Term(
                                phrase = phrase,
                                source_file = full_path,
                                **parse_term_kwargs(lang_m, tachy, True, True)
                            )
                            # terms.append(term)
                            try:
                                term.save()
                            except IntegrityError as e:
                                raise ValueError(f"term '{tachy}' (lexical synonym) raised {e}")
                    # Term.objects.bulk_create(terms)
                else:
                    defs = yaml.load(f.read(), settings.YAML_LOADER)
                    for tachy, phrase in defs.items():
                        carpet_phrase = StrPhrase(lang_m, phrase)
                        carpet_phrase.extend(Depth.VOCAB, False)
                        term = Term(
                            phrase = register_phrase(carpet_phrase),
                            source_file = full_path,
                            **parse_term_kwargs(lang_m, tachy, True, True),
                        )
                        try:
                            term.save()
                        except IntegrityError as e:
                            raise ValueError(f"term '{tachy}' raised {e}")
        else: print(f"skipping '{full_path}'")


def register_dictionaries(clear=True):
    if clear:
        Phrase.objects.all().delete() # phrases cascade
    for dict_props in settings.DICTIONARIES:
        iso_lang = SpacyLangModel.get_from_name(dict_props['lang'])
        iso_lang.nlp
        register_dictionary(dict_props['path'], iso_lang)
