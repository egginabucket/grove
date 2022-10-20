from django.contrib import admin
from language import models

admin.site.register([
    models.Language,
    models.SpacyLanguageModel,
    models.SpacyModelSize,
    models.SpacyModelType,
    models.PosTag,
])
