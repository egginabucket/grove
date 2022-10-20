from typing import Optional, Generator, Tuple, Union
from logging import warn
from music21.key import Key, KeySignature
from music21.stream.base import Stream, Score
from music21.note import Rest
from music21.metadata import Metadata
from music21.tempo import MetronomeMark
from spacy.tokens import Token
from django.conf import settings
from language.models import Language, SpacyLanguageModel
from carpet.base import AbstractPhrase, Depth, Suffix
from carpet.models import apply_model_phrase, Term
from carpet.m21 import DOWN_DEGREE, UP_DEGREE, phrase_to_m21
from spacy.glossary import GLOSSARY

PREPEND_DEPS = {'nsubj'}
COMM_REST = Rest('quarter')
PERI_REST = Rest('whole')

class WrapperPhrase(AbstractPhrase):
    def __init__(self,
        child: AbstractPhrase,
        multiplier: int = 1,
        count: Optional[int] = None,
        pitch_change: Optional[str] = None,
        suffix: Optional[str] = None,
        ):
        self.child = child
        self.lang = child.lang
        self.multiplier = multiplier
        self.count = count
        self.pitch_change = pitch_change
        self.suffix = suffix

    def get_children(self) -> Generator[AbstractPhrase, None, None]:
        yield self.child

class DepArrangement:
    pass # TODO


def token_to_m21(token: Token, key: Key, nucleus_deg: int, add_lyrics: bool, lang: Optional[Language] = None) -> Tuple[Stream, int]:
    if not lang:
        lang = Language.objects.get(code=token.lang_)
    stream = Score()
    phrase = AbstractPhrase()
    phrase.extend(Depth.LEXICAL, False)
    if token.pos_ == 'PUNCT':
        punct_type = token.morph.get('PunctType')
        if punct_type == ['Peri']:
            #if token.text == '?': pass
            stream.append(PERI_REST)
        elif punct_type == ['Comm']:
            stream.append(COMM_REST)
    elif token.pos_ not in ['PNOUN', 'AUX']:
        term = None
        try:
            term = Term.objects.get(
                language = lang,
                term = token.lemma_,
                pos_tag__abbr = token.pos_
            )
        except Term.DoesNotExist:
            warn(f"{token.pos_}:{token.lemma_} not found") # TODO
        if term:
            phrase = apply_model_phrase(lang, term.phrase)
        if 'Plur' in token.morph.get('Number'):
            phrase = WrapperPhrase(phrase, multiplier=2)
    prepend_tokens = []
    append_tokens = []
    for child in token.children:
        append_token = True
        if child.dep_ == 'neg':
            phrase = WrapperPhrase(phrase, suffix=Suffix.NOT)
            append_token = False
        elif child.pos_ == 'PUNCT' and child.text == '?':
            phrase = WrapperPhrase(phrase, suffix=Suffix.WHAT)
        elif child.dep_ == 'nummod':
            try: # TODO
                count = int(child.text)
            except ValueError:
                count = 2
            phrase = WrapperPhrase(phrase, count=count) # TODO: let user change?
        if append_token:
            if child.dep_ in PREPEND_DEPS:
                prepend_tokens.append(child)
            else:
                append_tokens.append(child)
            
    for child_token in prepend_tokens:
        child_stream, nucleus_deg = token_to_m21(child_token, key, nucleus_deg, add_lyrics, lang)
        stream.append(child_stream)
    
    phrase.extend(Depth.LEXICAL, True)
    phrase_stream, nucleus_deg = phrase_to_m21(phrase, key, nucleus_deg, add_lyrics)
    stream.append(phrase_stream)

    for child_token in append_tokens:
        child_stream, nucleus_deg = token_to_m21(child_token, key, nucleus_deg, add_lyrics, lang)
        stream.append(child_stream)

    return stream.flatten(), nucleus_deg


def str_to_score(lang_m: SpacyLanguageModel, text: str, add_lyrics=True, key=settings.DEFAULT_KEY, tempo='presto') -> Stream:
    lemmatizer = lang_m.nlp.get_pipe('lemmatizer')
    lemmatizer.labels
    doc = lang_m.nlp(text)
    stream = Stream()
    nucleus_deg = 0
    for sent in doc.sents:
        for token in sent:
            if token.dep_ == 'ROOT':
                substream, nucleus_deg = token_to_m21(token, key, nucleus_deg, add_lyrics, lang_m.language)
                stream.append(substream)
                nucleus_deg += DOWN_DEGREE
        nucleus_deg += UP_DEGREE
    score = Score()
    if tempo:
        score.append(MetronomeMark(tempo))
    score.append(KeySignature(key.sharps))
    score.append(stream.flatten())
    score.insert(0, Metadata())
    score.metadata.title = text
    score.metadata.add('software', 'Grove')
    return score.flatten()
