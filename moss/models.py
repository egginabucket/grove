from unicodedata import category
from django.db import models as m

RECURSIVE = -1

class NotesModel(m.Model):
    notes = m.TextField(null=True)

    class Meta:
        abstract = True

# https://universaldependencies.org/u/pos/
# used in spacy, 'universal' tagset in nltk
class PosTag(m.Model):
    class Category(m.IntegerChoices):
        OPEN_CLASS = 0, 'Open class'
        CLOSED_CLASS = 1, 'Closed class'
        OTHER = 2, 'Other'

    abbr = m.CharField(verbose_name='abbreviation', max_length=5)
    name = m.CharField(max_length=126)
    category = m.SmallIntegerField(choices=Category.choices)

    def __save__(self, *args, **kwargs):
        self.abbr = self.abbr.upper()
        self.description = self.description.lower()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.abbr
    
    class Meta:
        verbose_name = 'Universal POS tag'


class CoreDefinition(NotesModel):
    term = m.CharField(max_length=254, unique=True)
    phrase = m.TextField(verbose_name='definition in LilyPond', null=True)

    def __str__(self):
        return self.term


class Definition(NotesModel):
    term = m.CharField(max_length=254) # removed unique constraints
    pos_tag = m.ForeignKey(PosTag, on_delete=m.PROTECT)
    core_synonym = m.ForeignKey(CoreDefinition, related_name='synonyms', null=True, on_delete=m.CASCADE)
    carpet_phrase = m.ForeignKey('CarpetPhrase', null=True, on_delete=m.SET_NULL)
    source_file = m.CharField(null=True, max_length=254)

    def simple_str(self) -> str:
        return f"{self.tag}:{self.term.replace(' ', '_')}"

    def save(self, *args, **kwargs):
        """
        if current_synonym := self.synonym:
            while current_synonym:
                if current_synonym.term == self.synonym.term:
                    raise ValueError('Synonym leading to self')
                current_synonym = self.synonym
            """
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.term
    
    class Meta:
        constraints = [
            m.UniqueConstraint('term', 'pos_tag', 'notes', name='unique_definition')
        ]


class CarpetPhrase(NotesModel):
    parent = m.ForeignKey('self', related_name='children', null=True, on_delete=m.CASCADE)
    index = m.SmallIntegerField(default=0)
    has_braces = m.BooleanField(default=False)
    tone_changes = m.CharField(max_length=126)
    suffixes = m.CharField(max_length=126)
    multiplier = m.PositiveSmallIntegerField()
    definition_child = m.ForeignKey(Definition, null=True, on_delete=m.SET_NULL)

    def get_children(self):
        return self.children.order_by('index')

    def save(self, *args, **kwargs):
        """
        if not self.carpet_child and not self.definition_child:
            raise ValueError('Child must be a definition or carpet phrase')
        if self.carpet_child and self.definition_child:
            raise ValueError('Child must be a definition or carpet phrase, not both')
        """
        
        return super().save(*args, **kwargs)
