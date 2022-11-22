import csv
import os
import subprocess
from typing import Generator, Optional

from nltk.corpus import wordnet2021
from nltk.corpus.reader import Synset

from spacy.displacy import serve
from spacy.glossary import GLOSSARY
from spacy.tokens import Token
from spacy.tokens.doc import Doc


OLD_CARPET_YAML_KEY_RE = r"\w+\.\w.\d{2}: "


def show_synsets(lemma: str, **kwargs):
    for synset in wordnet2021.synsets(lemma, **kwargs):
        synset: Synset
        print(
            "%s: %s (%s%s)"
            % (
                synset.name(),
                synset.definition(),
                ", ".join(synset.lemma_names()[:3]),
                "..." if len(synset.lemma_names()) > 3 else "",
            )
        )


def libreoffice_displayer(path: str):
    subprocess.Popen(["libreoffice", "--calc", "--nologo", path])


def explain_token_dicts(doc: Doc) -> Generator[dict, None, None]:
    for token in doc:
        row = {
            "text": token.text,
            "lemma": token.lemma_,
            "dep": token.dep_,
            "tag": token.tag_,
            "pos": token.pos_,
            "head": token.head,
            "morph": str(token.morph),
        }
        for col in ("dep", "tag", "pos"):
            row[col + " exp"] = GLOSSARY[row[col]]
        yield row


def explain_doc(
    doc: Doc, path: Optional[str] = None, displayer=libreoffice_displayer
):
    if not path:
        path = "/tmp/grove-dev-doc-explain.csv"
    fieldnames = "head,text,lemma,dep,dep exp,tag,tag exp,pos,pos exp,morph"
    with open(path, "w") as f:
        writer = csv.DictWriter(f, fieldnames.split(","))
        writer.writeheader()
        writer.writerows(explain_token_dicts(doc))
    displayer(path)


def load_example(name: str) -> str:
    with open(os.path.join("example-texts", name + ".txt")) as f:
        return " ".join((line.strip() for line in f))
