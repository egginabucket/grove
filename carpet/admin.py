from django.contrib import admin
from carpet import models

admin.site.register([
    models.SynsetDef,
    models.Phrase,
    models.PhraseComposition,
])
