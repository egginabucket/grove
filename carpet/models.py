from functools import cached_property
from typing import Generator
from django.db import models
from language.models import Language, SpacyLanguageModel, PosTag
from maas.models import Lexeme
from carpet.base import AbstractPhrase, PitchChange, Suffix

class Phrase(models.Model, AbstractPhrase):
    pitch_change = models.CharField(choices=PitchChange.choices, null=True, max_length=1)
    multiplier = models.PositiveSmallIntegerField(default=1)
    count = models.PositiveSmallIntegerField(null=True)
    suffix = models.CharField(choices=Suffix.choices, null=True, max_length=1)
    lexeme = models.ForeignKey(Lexeme, null=True, on_delete=models.PROTECT)

    def get_children(self) -> Generator['Phrase', None, None]:
        for child_rel in self.child_rels.order_by('index'):
            child = apply_model_phrase(self.lang, child_rel.child)
            child.has_braces = child_rel.has_braces
            yield child
    
    def unwrapped_str(self) -> str:
        return str(self.lexeme) or ' '.join(map(str, self.get_children()))

def apply_model_phrase(lang: Language, phrase: Phrase):
    phrase.lang = lang
    return phrase

class PhraseComposition(models.Model):
    parent = models.ForeignKey(Phrase, related_name='child_rels', on_delete=models.CASCADE)
    child = models.ForeignKey(Phrase, related_name='parent_rels', on_delete=models.CASCADE)
    index = models.SmallIntegerField()
    has_braces = models.BooleanField(default=False)

    class Meta:
        unique_together = ('parent', 'index')
    
    def save(self, *args, **kwargs):
        if self.parent.lexeme:
            raise ValueError(f"Parent already has a lexeme: '{self.parent.lexeme}'")
        return super().save(*args, **kwargs)


def parse_to_term_kwargs(lang: SpacyLanguageModel, tachygraph: str, infer_pos_tag: bool, as_objs: bool) -> dict[str]:
    kwargs = {
        'language': lang.language,
    }
    kwargs['term'] = tachygraph.strip().replace('_', ' ')
    if ':' in tachygraph:
        kwargs['pos_tag__abbr'], kwargs['term'] = kwargs['term'].split(':')
        kwargs['pos_tag__abbr'] = kwargs['pos_tag__abbr'].upper()
    term_token = lang.nlp(kwargs['term'])[0]

    if term_token.lemma_ != kwargs['term']:
        print(f"WARNING: term '{kwargs['term']}' has lemma '{term_token.lemma_}'")

    if infer_pos_tag and 'pos_tag__abbr' not in kwargs:
        kwargs['pos_tag__abbr'] = term_token.pos_
    if as_objs and 'pos_tag__abbr' in kwargs:
        kwargs['pos_tag'] = PosTag.objects.get(abbr=kwargs.pop('pos_tag__abbr'))        
    return kwargs


class Term(models.Model):
    term = models.CharField(max_length=254)
    language = models.ForeignKey(Language, on_delete=models.PROTECT)
    pos_tag = models.ForeignKey(PosTag, on_delete=models.PROTECT)
    phrase = models.ForeignKey(Phrase, related_name='defined_terms', on_delete=models.CASCADE)
    source_file = models.CharField(null=True, max_length=254)

    @cached_property
    def tachygraph(self) -> str:
        return f"{self.pos_tag.abbr}:{self.term.replace(' ', '_')}"

    def __str__(self):
        return self.tachygraph

    class Meta:
        unique_together = ('term', 'language', 'pos_tag')
