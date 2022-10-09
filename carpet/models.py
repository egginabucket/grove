from typing import Generator
from django.db import models
from maas.models import Lexeme, PosTag
from carpet.common import AbstractPhrase, PitchChange, Suffix, nlp

class Phrase(models.Model, AbstractPhrase):
    has_braces = models.BooleanField(default=False)
    pitch_change = models.CharField(choices=PitchChange.choices, null=True, max_length=1)
    multiplier = models.PositiveSmallIntegerField(default=1)
    count = models.PositiveSmallIntegerField(null=True)
    suffix = models.CharField(choices=Suffix.choices, null=True, max_length=1)
    lexeme = models.ForeignKey(Lexeme, null=True, on_delete=models.PROTECT)

    def get_children(self) -> Generator['Phrase', None, None]:
        for child_rel in self.child_rels.order_by('index'):
            yield child_rel.child
    
    def unwrapped_str(self) -> str:
        return str(self.lexeme) or ' '.join(map(str, self.get_children()))

class PhraseComposition(models.Model):
    parent = models.ForeignKey(Phrase, related_name='child_rels', on_delete=models.CASCADE)
    child = models.ForeignKey(Phrase, related_name='parent_rels', on_delete=models.CASCADE)
    index = models.SmallIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint('parent', 'index', name='no_duplicate_subphrase_indices'),
        ]
    
    def save(self, *args, **kwargs):
        if self.parent.lexeme:
            raise ValueError(f"Parent already has a lexeme: '{self.parent.lexeme}'")
        return super().save(*args, **kwargs)

def parse_to_term_kwargs(raw_str: str, infer_pos_tag: bool, pos_tag_as_obj: bool) -> dict[str]:
    kwargs = dict()
    kwargs['english'] = raw_str.strip().lower().replace('_', ' ')
    if ':' in raw_str:
        kwargs['pos_tag__abbr'], kwargs['english'] = kwargs['english'].split(':')
        kwargs['pos_tag__abbr'] = kwargs['pos_tag__abr'].upper()
    elif infer_pos_tag:
        kwargs['pos_tag__abbr'] = nlp(raw_str)[0].pos_
    if kwargs.get('pos_tag__abbr') and pos_tag_as_obj:
        kwargs['pos_tag'] = PosTag.objects.get(abbr=kwargs.pop('pos_tag__abbr'))        
    return kwargs


class Term(models.Model):
    english = models.CharField(max_length=254)
    pos_tag = models.ForeignKey(PosTag, on_delete=models.PROTECT)
    phrase = models.ForeignKey(Phrase, related_name='defined_term', on_delete=models.CASCADE)
    source_file = models.CharField(null=True, max_length=254)

    def parse_from_tachygraph(self, raw_str: str):
        kwargs = parse_to_term_kwargs(raw_str, True, True)
        self.pos_tag = kwargs['pos_tag']
        self.english = kwargs['english']

    def tachygraph(self) -> str:
        return f"{self.pos_tag.abbr}:{self.english.replace(' ', '_')}"

    def __str__(self):
        return self.english

    class Meta:
        constraints = [
            models.UniqueConstraint('english', 'pos_tag', name='no_duplicate_definitions'),
        ]
