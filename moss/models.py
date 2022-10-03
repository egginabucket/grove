from django.db import models as m

RECURSIVE = -1

class NotesModel(m.Model):
    notes = m.TextField(null=True)

    class Meta:
        abstract = True

class CoreDefinition(NotesModel):
    term = m.CharField(max_length=254, unique=True)
    phrase = m.TextField(verbose_data='definition in LilyPond', null=True)

class Definition(NotesModel):
    term = m.CharField(max_length=254, unique=True)
    core_synonym = m.ForeignKey(CoreDefinition, related_name='synonyms', null=True, on_delete=m.CASCADE)
    carpet_phrase = m.ForeignKey('CarpetPhrase', null=True, on_delete=m.SET_NULL)
    source_file = m.CharField(null=True, max_length=254)

    def save(self, *args, **kwargs):
        if current_synonym := self.synonym:
            while current_synonym:
                if current_synonym.term == self.synonym.term:
                    raise ValueError('Synonym leading to self')
                current_synonym = self.synonym
        super().save(*args, **kwargs)

    def __str__(self):
        return self.term


class CarpetPhrase(NotesModel):
    parent = m.ForeignKey('self', related_name='children', null=True, on_delete=m.CASCADE)
    index = m.SmallIntegerField(default=1)
    has_braces = m.BooleanField(default=False)
    tone_changes = m.CharField(max_length=126)
    suffixes = m.CharField(max_length=126)
    multiplier = m.PositiveSmallIntegerField()
    definition_child = m.ForeignKey(Definition, null=True, on_delete=m.SET_NULL)

    def get_children(self):
        return self.children().order_by('index')

    def save(self, *args, **kwargs):
        if not self.carpet_child and not self.definition_child:
            raise ValueError('Child must be a definition or carpet phrase')
        if self.carpet_child and self.definition_child:
            raise ValueError('Child must be a definition or carpet phrase, not both')
        
        super().save(*args, **kwargs)
