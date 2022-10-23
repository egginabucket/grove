from django.contrib import admin
from language import models


@admin.register(models.Lang)
class LangAdmin(admin.ModelAdmin):
    list_display = (
        'ref_name',
        'part_3',
        'part_1',
        'scope',
        'lang_type',
        'is_wordnet_supported',
        'macrolang',
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


@admin.register(models.LangName)
class LangNameAdmin(admin.ModelAdmin):
    list_display = (
        'printable',
        'lang'
    )
    search_fields = (
        'printable',
        'inverted',
        'lang__part_3',
        'lang__part_1',
        'lang__part_2b',
    )

@admin.register(models.LangSubtagRegistry)
class LangSubtagRegistry(admin.ModelAdmin):
    list_display = (
        'file_date',
        'saved',
    )

@admin.register(models.LangTag)
class LangTagAdmin(admin.ModelAdmin):
    list_display = (
        'subtag',
        'tag',
        'tag_type',
        'deprecated',
        'added',
        'scope',
        'pref_value',
        'macrolang',
    )
    search_fields = (
        'tag',
        'subtag',
    )


@admin.register(models.LangTagDescription)
class LangTagDescriptionAdmin(admin.ModelAdmin):
    list_display = (
        'text',
        'index',
        'tag',
    )
    search_fields = (
        'text',
        'index',
        'tag__tag',
        'tag__subtag',
    )


@admin.register(models.LangTagPrefix)
class LangTagPrefixAdmin(admin.ModelAdmin):
    list_display = LangTagDescriptionAdmin.list_display
    search_fields = LangTagDescriptionAdmin.search_fields


@admin.register(models.SpacyLangModel)
class SpacyLangModelAdmin(admin.ModelAdmin):
    pass


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
    )
