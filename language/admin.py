from django.contrib import admin
from language import models


@admin.register(models.IsoLang)
class LangAdmin(admin.ModelAdmin):
    list_display = (
        'ref_name',
        'part_3',
        'part_1',
        'scope',
        'lang_type',
        'is_wordnet_supported',
        'macrolanguage',
    )
    search_fields = (
        'ref_name',
        'part_3',
        'part_1',
        'part_2b',
    )
    list_filter = (
        'is_wordnet_supported',
    )


@admin.register(models.IsoLangName)
class IsoLangNameAdmin(admin.ModelAdmin):
    list_display = (
        'printable',
        'iso_lang'
    )
    search_fields = (
        'printable',
        'inverted',
        'iso_lang__part_3',
        'iso_lang__part_1',
        'iso_lang__part_2b',
    )


@admin.register(models.IanaSubtagRegistry)
class LangSubtagRegistry(admin.ModelAdmin):
    list_display = (
        'file_date',
        'saved',
    )


@admin.register(models.Subtag)
class LangTagAdmin(admin.ModelAdmin):
    list_display = (
        'subtag',
        'tag',
        'tag_type',
        'iana_deprecated',
        'iana_added',
        'scope',
        'pref_value',
        'macrolanguage',
    )
    search_fields = (
        'tag',
        'subtag',
    )


@admin.register(models.SubtagDescription)
class LangTagDescriptionAdmin(admin.ModelAdmin):
    list_display = (
        'text',
        'index',
        'subtag',
    )
    search_fields = (
        'text',
        'index',
        'subtag__tag',
        'subtag__subtag',
    )


@admin.register(models.SubtagPrefix)
class LangTagPrefixAdmin(admin.ModelAdmin):
    list_display = (
        'text',
        'index',
        'subtag',
    )
    search_fields = (
        'text',
        'index',
        'subtag__tag',
        'subtag__subtag',
    )
    # list_display = LangTagDescriptionAdmin.list_display
    # search_fields = LangTagDescriptionAdmin.search_fields


@admin.register(models.Script)
class ScriptAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'no',
        'name_en',
        'pva',
        'unicode_version',
        'script_date'
    )
    search_fields = (
        'code',
        'no',
        'name_en',
        'name_fr',
        'pva',
    )


@admin.register(models.SpacyLangModel)
class SpacyLangModelAdmin(admin.ModelAdmin):
    list_display = (
        'iso_lang',
        'model_size',
        'model_type',
        'genre',
        'package_version',
        'downloaded',
    )
    search_fields = (
        'iso_lang__ref_name'
        'iso_lang__part_3',
        'iso_lang__part_1',
        'iso_lang__part_2b',
        'version',
    )
    list_filter = (
        'downloaded',
    )
    actions = ['download']
    @admin.action(description='Download SpaCy package')
    def download(self, _, queryset):
        for obj in queryset:
            obj.download()


@admin.register(models.SpacyModelSize)
class SpacyModelSizeAdmin(admin.ModelAdmin):
    pass


@admin.register(models.SpacyModelType)
class SpacyModelTypeAdmin(admin.ModelAdmin):
    pass


@admin.register(models.PosTag)
class PosTagAdmin(admin.ModelAdmin):
    list_display = (
        'abbr',
        'name',
        'category',
    )
