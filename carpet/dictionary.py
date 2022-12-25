import warnings
from pathlib import Path

import yaml
from django.conf import settings
from django.db.utils import IntegrityError
from jangle.models import LanguageTag
from nltk.corpus.reader import Synset
from yaml.error import MarkedYAMLError

from carpet.models import SynsetDef
from carpet.parser import StrPhrase
from carpet.wordnet import wordnet


class DictionaryLoader:
    def __init__(self, lang: LanguageTag) -> None:
        self.lang = lang
        self.registered_paths = []

    def register(self, path: Path) -> None:
        if path in self.registered_paths:
            return
        if not path.exists():
            return
        if path.is_dir():
            for subpath in path.glob("*"):
                self.register(subpath)
        elif path.is_file():
            if path.suffix not in (".yaml", ".yml"):
                warnings.warn(f"skipping {path}")
                return
            with path.open() as f:
                try:
                    defs: dict = yaml.load(f.read(), settings.YAML_LOADER)
                except MarkedYAMLError as e:
                    raise ValueError(f"invalid yaml file at {path}") from e
                for requirement in defs.pop("requires", []):
                    assert isinstance(requirement, str)
                    req_path = (path.parent / requirement).resolve()
                    self.register(req_path.with_suffix(".yaml"))
                    self.register(req_path.with_suffix(".yml"))
                for phrase, synset_names in defs.items():
                    assert isinstance(phrase, str)
                    assert isinstance(synset_names, list)
                    carpet_phrase = StrPhrase(phrase, self.lang)
                    try:
                        phrase_obj = carpet_phrase.save()
                    except Exception as e:
                        raise ValueError(f"at '{path}'") from e
                    for name in synset_names:
                        assert isinstance(name, str)
                        try:
                            synset: Synset = wordnet.synset(name)  # type: ignore
                        except ValueError as e:
                            raise ValueError(f"synset '{name}'") from e
                        if synset.name() != name:
                            warnings.warn(
                                f"given name '{name}' at {path} "
                                f"does not match {synset}"
                            )
                        try:
                            existing = SynsetDef.objects.get_from_synset(
                                synset
                            )
                            raise IntegrityError(
                                f"{synset} at {path} "
                                f"already defined at {existing.source_file}"
                            )
                        except SynsetDef.DoesNotExist:
                            pass
                        def_ = SynsetDef(
                            phrase=phrase_obj,
                            pos=synset.pos(),
                            wn_offset=synset.offset(),
                            source_file=path.suffix,
                        )
                        try:
                            def_.save()
                        except IntegrityError as e:
                            raise IntegrityError(
                                f"synset def '{name}' at {path}"
                            ) from e
        else:
            raise ValueError(f"invalid path {path}")
        self.registered_paths.append(path)
