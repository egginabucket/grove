from django.contrib import admin
from translator import models

admin.site.register(
    [
        models.GoogleLanguage,
        models.SpacyModelSize,
        models.SpacyModelType,
    ]
)



@admin.register(models.SpacyLanguage)
class SpacyLangModelAdmin(admin.ModelAdmin):
    list_display = [
        'iso_lang',
        'model_size',
        'model_type',
        'genre',
        'package_version',
        'downloaded',
   ]
    search_fields = [
        'iso_lang__ref_name'
        'iso_lang__part_3',
        'iso_lang__part_1',
        'iso_lang__part_2b',
        'version',
   ]
    list_filter = [
        'downloaded',
   ]
    actions = ['download']
    @admin.action(description='Download SpaCy package')
    def download(self, _, queryset):
        for obj in queryset:
            obj.download()

