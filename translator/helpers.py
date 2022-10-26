#from spacy.tokens import Token
import os
from typing import Optional, Generator
from spacy.tokens.doc import Doc
from spacy.glossary import GLOSSARY
#from spacy.displacy import serve
import subprocess
import csv


def libreoffice_displayer(path: str):
    subprocess.Popen(['libreoffice', '--calc', '--nosplash', path])


def explain_token_dicts(doc: Doc) -> Generator[dict[str, str], None, None]:
    for token in doc:
        row = {
            'text': token.text,
            'lemma': token.lemma_,
            'dep': token.dep_,
            'tag': token.tag_,
            'pos': token.pos_,
            'head': token.head,
            'morph': str(token.morph),
        }
        for col in ('dep', 'tag', 'pos'):
            row[col+' exp'] = GLOSSARY[row[col]]
        yield row


def explain_doc(doc: Doc, path: Optional[str] = None, displayer=libreoffice_displayer):
    if not path:
        path = '/tmp/grove-dev-doc-explain.csv'
    fieldnames = 'head,text,lemma,dep,dep exp,tag,tag exp,pos,pos exp,morph'
    with open(path, 'w') as f:
        writer = csv.DictWriter(f, fieldnames.split(','))
        writer.writeheader()
        writer.writerows(explain_token_dicts(doc))
    displayer(path)
