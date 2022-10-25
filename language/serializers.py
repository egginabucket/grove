from rest_framework import serializers
from language import models


class LangSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Lang
        fields = [
            'ref_name',
            'part_3',
            'part_1',
            'part_2b',
            'part_2t',
            'lang_type',
            'scope',
            'comment',
            'macrolanguage',
            'is_wordnet_supported',
        ]


class ScriptSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Script
        fields = [
            'code',
            'no',
            'name_en',
            'name_fr',
            'pva',
            'unicode_version',
            'script_date'
        ]


class SpacyLangModelSerializer(serializers.ModelSerializer):
    language = LangSerializer()
    model_type = serializers.SlugRelatedField('abbr')
    model_size = serializers.SlugRelatedField('abbr')

    class Meta:
        model = models.SpacyLangModel
        fields = [
            'name',
            'full_name',
            'language',
            'model_type',
            'genre',
            'model_size',
            'package_version',
            'docs_url',
            'github_meta_url',
        ]


class PosTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PosTag
        fields = ['abbr', 'name', 'category']
