from pathlib import Path
from typing import Optional

import yaml
from django.conf import settings
from spacy.tokens import Token

from carpet.parser import AbstractPhrase, StrPhrase

# acts as cache (lang int -> pos_/tag_ -> "text" -> phrase)
_tokens: dict[int, dict[str, dict[str, StrPhrase]]] = {}

_base_path = Path(__file__).resolve().parent


def token_phrase(token: Token) -> Optional[AbstractPhrase]:
    if token.lang in _tokens:
        lang_tokens = _tokens[token.lang]
        tag_tokens = {}
        if token.tag_ in lang_tokens:
            tag_tokens = lang_tokens[token.tag_]
        elif token.pos_ in lang_tokens:
            tag_tokens = lang_tokens[token.pos_]
        if tag_tokens:
            for text in [token.norm_, token.lemma_, token.text]:
                if text in tag_tokens:
                    return tag_tokens[text]
    else:
        for lang_path in _base_path.glob(token.lang_):
            if not lang_path.is_dir():
                continue
            _tokens[token.lang] = {}
            for fn in lang_path.rglob("*"):
                if not fn.is_file():
                    continue
                if fn.suffix not in (".yml", ".yaml"):
                    continue
                tag = fn.name.split(".")[0].upper()
                with fn.open() as f:
                    _tokens[token.lang][tag] = {
                        key: StrPhrase(val)
                        for key, val in yaml.load(
                            f, settings.YAML_LOADER
                        ).items()
                    }
            return token_phrase(token)
