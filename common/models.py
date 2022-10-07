from django.db import models

# https://universaldependencies.org/u/pos/
# used in spacy, 'universal' tagset in nltk
class PosTag(models.Model):
    class Category(models.IntegerChoices):
        OPEN_CLASS = 0, 'open class'
        CLOSED_CLASS = 1, 'closed class'
        OTHER = 2, 'other'

    abbr = models.CharField(verbose_name='abbreviation', max_length=5)
    name = models.CharField(max_length=126)
    category = models.SmallIntegerField(choices=Category.choices)

    def __save__(self, *args, **kwargs):
        self.abbr = self.abbr.upper()
        self.description = self.description.lower()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.abbr
    
    class Meta:
        verbose_name = 'universal POS tag'