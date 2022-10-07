from curses import raw
from django.db import models
from django.conf import settings
from common.models import PosTag
from maas.models import Lexeme
from carpet.common import AbstractPhrase
import spacy

nlp = spacy.load(settings.SPACY_PACKAGE)

class Phrase(models.Model, AbstractPhrase):
    class ToneChange(models.TextChoices):
        UP = '+', 'up'
        DOWN = '-', 'down'
        LAST = '@', 'last'
        # UNISON = None, 'unison'
    
    class Suffix(models.TextChoices):
        QUESTION = '?', 'question'
        NOT = '!', 'not'
    
    parent = models.ForeignKey('self', related_name='children', null=True, on_delete=models.CASCADE)
    index = models.SmallIntegerField(default=0)
    has_braces = models.BooleanField(default=False)
    tone_change = models.CharField(choices=ToneChange.choices, null=True, max_length=1)
    multiplier = models.PositiveSmallIntegerField()
    count = models.PositiveSmallIntegerField(null=True)
    suffix = models.CharField(choices=Suffix.choices, null=True, max_length=1)
    lexeme = models.ForeignKey(Lexeme, null=True, on_delete=models.PROTECT)

    def get_children(self) -> models.BaseManager['Phrase']:
        yield from self.children.order_by('index')
    
    def unwrapped_str(self) -> str:
        return str(self.lexeme) or ' '.join(map(str, self.get_children()))

    def save(self, *args, **kwargs):
        if self.parent and (lexeme := self.parent.lexeme):
            raise ValueError(f"Parent already has a lexeme: '{lexeme}'")
        return super().save(*args, **kwargs)
        

def parse_to_term_kwargs(raw_str: str, infer_pos_tag=False, pos_tag_as_obj=False) -> dict[str]:
    kwargs = dict()
    kwargs['english'] = raw_str.strip().lower().replace('_', ' ')
    if ':' in raw_str:
        kwargs['pos_tag__abr'], kwargs['english'] = kwargs['english'].split(':')
        kwargs['pos_tag__abr'] = kwargs['pos_tag__abr'].upper()
    elif infer_pos_tag:
        kwargs['pos_tag__abr'] = nlp(raw_str)[0].pos_
    if kwargs.get('pos_tag__abr') and pos_tag_as_obj:
        kwargs['pos_tag'] = PosTag.objects.get(abbr=kwargs.pop('pos_tag__abr'))        
    return kwargs


class Term(models.model):
    english = models.CharField(max_length=254)
    pos_tag = models.ForeignKey(PosTag, on_delete=models.PROTECT)
    phrase = models.OneToOneField(Phrase, related_name='defined_term', on_delete=models.CASCADE)
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
