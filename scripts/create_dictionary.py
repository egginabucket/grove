import os
import yaml
try: from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader
    
from moss.models import CoreDefinition, Definition, CarpetPhrase

CORE_DEFS_PATH = os.path.join('moss', 'core_defs.yaml')
CORE_TERMS_PATH = os.path.join('moss', 'core_terms.yaml')
CUSTOM_VOCAB_PATH = os.path.join('moss', 'custom_vocab')

# TODO

def run():
    if not input("Rebuild dictionary from YAML files? y/N: ").strip().upper().startswith('Y'):
        return
    
    Definition.objects.all().delete()
    CarpetPhrase.objects.all().delete()

    with open(CORE_DEFS_PATH) as f:
        defs = yaml.load(f.read(), SafeLoader)
        CoreDefinition.objects.bulk_create([CoreDefinition(
            term = key,
            phrase = val,
        ) for key, val in defs.items()])

    with open(CORE_TERMS_PATH) as f:
        defs = yaml.load(f.read(), SafeLoader)
        definitions = []
        for key, val in defs.items():
            definition, _ = CoreDefinition.objects.get_or_create(term=key)
            definitions.extend([Definition(
                core_synonym = definition,
                term = term,
                source_file = CORE_TERMS_PATH,
            ) for term in val])
        Definition.objects.bulk_create(definitions)
    
    for dir in os.listdir(CUSTOM_VOCAB_PATH):
        dir = os.path.join(CUSTOM_VOCAB_PATH, dir)
        if not os.path.isdir(dir): continue
        for yaml_file in os.listdir(dir):
            yaml_file = os.path.join(dir, yaml_file)
            if not (os.path.isfile(yaml_file) and yaml_file.endswith('.yaml')): continue
            with open(yaml_file) as f:
                defs = yaml.load(f.read(), SafeLoader)
                for key, val in defs.items():
                    Definition.objects.create( 
                        term = key,
                        definition = TermDefinition.objects.create(is_core=False, phrase=val),
                        source_file = yaml_file,
                    )
    
