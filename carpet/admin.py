from django.contrib import admin
from carpet import models

admin.site.register([
    models.Term,
    models.Phrase,
    models.PhraseComposition,
])
