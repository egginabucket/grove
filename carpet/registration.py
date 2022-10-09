import os
import yaml
from django.db.utils import IntegrityError
from django.conf import settings
from carpet.common import AbstractPhrase, Depth
from carpet.models import Phrase, PhraseComposition, Term
from carpet.parser import StrPhrase
from maas.models import Lexeme

LEXICAL_SYNONYMS_PATH = os.path.join('carpet', 'lexical_synonyms.yaml')

def register_phrase(phrase: AbstractPhrase) -> Phrase:
    # recursive, lexemes not supported
    if isinstance(phrase, Phrase):
        return phrase
    obj = Phrase.objects.create(
        has_braces = phrase.has_braces,
        pitch_change = phrase.pitch_change,
        multiplier = phrase.multiplier,
        suffix = phrase.suffix,
        count = phrase.count,
        lexeme = phrase.lexeme,
    )
    for i, child in enumerate(phrase.children):
        PhraseComposition.objects.create(
            parent = obj,
            child = register_phrase(child),
            index = i,
        )
    return obj


def register_dictionary(path: str):
    for subpath in sorted(os.listdir(path)):
        full_path = os.path.join(path, subpath)
        if os.path.isdir(full_path):
            register_dictionary(full_path)
        elif os.path.isfile(full_path) and full_path.endswith('.yaml'):       
            with open(full_path) as f:
                defs = yaml.load(f.read(), settings.YAML_LOADER)
                for tachy, phrase in defs.items():
                    carpet_phrase = StrPhrase(phrase)
                    carpet_phrase.extend(Depth.VOCAB, False)
                    term = Term(
                        phrase = register_phrase(carpet_phrase),
                        source_file = full_path,
                    )
                    term.parse_from_tachygraph(tachy)
                    try:
                        term.save()
                    except IntegrityError as e:
                        raise ValueError(f"term '{tachy}' raised {e}")


def register_dictionaries():
    for dict_path in settings.DICTIONARY_PATHS:
        register_dictionary(dict_path)


def register_lexical_synonyms(path=LEXICAL_SYNONYMS_PATH, clear=True):
    if clear: # also clears dictionary
        Phrase.objects.all().delete()
    
    with open(LEXICAL_SYNONYMS_PATH) as f:
        terms = []
        for lexeme_english, tachys in yaml.load(f.read(), settings.YAML_LOADER).items():
            lexeme, created = Lexeme.objects.get_or_create(english=lexeme_english)
            if created:
                print(f"created unknown lexeme '{lexeme_english}'")
            phrase = Phrase.objects.create(lexeme=lexeme)
            for tachy in tachys:
                term = Term(
                    phrase = phrase,
                    source_file = path,
                )
                term.parse_from_tachygraph(tachy)
                terms.append(term)
        Term.objects.bulk_create(terms)