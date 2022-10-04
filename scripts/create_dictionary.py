import os
import yaml
try: from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader

from moss import carpet, models
    

CORE_DEFS_PATH = os.path.join('moss', 'core_defs.yaml')
CORE_SYNONYMS_PATH = os.path.join('moss', 'core_synonyms.yaml')
CUSTOM_VOCAB_PATH = os.path.join('moss', 'custom_vocab')

# TODO

def run():
    if not input("Rebuild dictionary from YAML files? y/N: ").strip().upper().startswith('Y'):
        return
    
    models.CoreDefinition.objects.all().delete()
    models.Definition.objects.all().delete()
    models.CarpetPhrase.objects.all().delete()

    with open(CORE_DEFS_PATH) as f:
        defs = yaml.load(f.read(), SafeLoader)
        models.CoreDefinition.objects.bulk_create([models.CoreDefinition(
            term = key,
            phrase = val,
        ) for key, val in defs.items()])

    with open(CORE_SYNONYMS_PATH) as f:
        defs = yaml.load(f.read(), SafeLoader)
        definitions = []
        terms = []
        for key, val in defs.items():
            for term in val:
                if term in terms: print(term)
                terms.append(term)
            definition, _ = models.CoreDefinition.objects.get_or_create(term=key)
            definitions.extend([models.Definition(
                **carpet.def_to_model_kwargs(term),
                core_synonym = definition,
                source_file = CORE_SYNONYMS_PATH,
            ) for term in val])
        models.Definition.objects.bulk_create(definitions)
    
    for dir in os.listdir(CUSTOM_VOCAB_PATH):
        dir = os.path.join(CUSTOM_VOCAB_PATH, dir)
        if not os.path.isdir(dir): continue
        for yaml_file in os.listdir(dir):
            yaml_file = os.path.join(dir, yaml_file)
            if not (os.path.isfile(yaml_file) and yaml_file.endswith('.yaml')): continue
            with open(yaml_file) as f:
                defs = yaml.load(f.read(), SafeLoader)
                for term, val in defs.items():
                    carpet_phrase = carpet.StrPhrase(val)
                    carpet_phrase.extend(carpet.Depth.RECURSIVE)
                    models.Definition.objects.create( 
                         **carpet.def_to_model_kwargs(term),
                        carpet_phrase = carpet.save_definition(carpet_phrase),
                        source_file = yaml_file,
                    )
    
