import yaml
try: from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader
from moss.models import PosTag

POS_PATH = 'universal_pos.yaml'

def run():
    with open(POS_PATH) as f:
        pos_tags = []
        for cat, tags in yaml.load(f.read(), SafeLoader).items():
            category = PosTag.Category.OTHER
            for i, choice in PosTag.Category.choices:
                if cat == choice:
                    category = i
                    break
            for abbr, name in tags.items():
                pos_tags.append(PosTag(abbr=abbr, name=name, category=category))
        PosTag.objects.bulk_create(pos_tags)


