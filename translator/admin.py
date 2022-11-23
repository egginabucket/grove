from django.contrib import admin
from translator import models

admin.site.register(
    [
        models.GoogleLanguage,
        models.SpacyLanguage,
        models.SpacyModelSize,
        models.SpacyModelType,
    ]
)
