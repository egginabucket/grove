from django.contrib import admin
from maas import models

admin.site.register([
    models.Lexeme,
    models.LexemeFlexNote,
    models.FlexNote,
    models.PosTag,
])
