from django.contrib import admin
from maas import models

admin.site.register([
    models.Lexeme,
    models.LexemeTranslation,
    models.LexemeFlexNote,
    models.FlexNote,
])
