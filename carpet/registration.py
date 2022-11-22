import os
import warnings
from dataclasses import dataclass, field

import yaml
from django.conf import settings
from django.db.utils import IntegrityError
from jangle.models import LanguageTag
from nltk.corpus import wordnet2021
from nltk.corpus.reader import Synset, WordNetCorpusReader
from yaml.error import MarkedYAMLError

from carpet.models import Phrase, SynsetDef
from carpet.parser import StrPhrase


@dataclass
class DictionaryLoader:
    lang: LanguageTag
    wn: WordNetCorpusReader
    registered_paths: list[str] = field(default_factory=list)

    def register(self, path: str):
        if path in self.registered_paths:
            return
        if os.path.isdir(path):
            for subpath in os.listdir(path):
                self.register(os.path.join(path, subpath))
        elif os.path.isfile(path):
            base_name = os.path.basename(path)
            if base_name.split(os.extsep)[-1] != "yaml":
                warnings.warn(f"skipping file {path}")
                return
            with open(path) as f:
                try:
                    defs: dict = yaml.load(f.read(), settings.YAML_LOADER)
                except MarkedYAMLError as e:
                    raise ValueError(f"invalid yaml file at {path}") from e
                try:
                    requirements = defs.pop("requires")
                except KeyError:
                    raise ValueError(f"{path} missing requirements")
                for requirement in requirements:
                    requirement_path = os.path.join(
                        os.path.dirname(path),
                        os.extsep.join([requirement, "yaml"]),
                    )
                    self.register(requirement_path)
                for phrase, synset_names in defs.items():
                    phrase: str
                    synset_names: list[str]
                    carpet_phrase = StrPhrase(self.lang, self.wn, phrase)
                    try:
                        phrase_obj = carpet_phrase.save()
                    except Exception as e:
                        raise ValueError(f"at '{path}'") from e
                    for name in synset_names:
                        try:
                            synset: Synset = self.wn.synset(name)
                        except ValueError as e:
                            raise ValueError(f"synset '{name}'") from e
                        if synset.name() != name:
                            warnings.warn(
                                f"given name '{name}' at {path} "
                                f"does not match {synset}"
                            )
                        try:
                            def_ = SynsetDef.objects.get_from_synset(synset)
                            raise IntegrityError(
                                f"synset {synset} at {path} "
                                f"already defined at {def_.source_file}"
                            )
                        except SynsetDef.DoesNotExist:
                            pass
                        def_ = SynsetDef(
                            phrase=phrase_obj,
                            pos=synset.pos(),
                            wn_offset=synset.offset(),
                            source_file=path,
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


def register_dictionaries(clear=True):
    if clear:
        Phrase.objects.all().delete()  # phrases cascade
    wordnet2021.ensure_loaded()
    for dict_props in settings.DICTIONARIES:
        path = dict_props["path"]
        lang = LanguageTag.objects.get_from_str(dict_props["lang"])
        loader = DictionaryLoader(lang, wordnet2021)  # type: ignore
        loader.register(path)
