from rest_framework import serializers as s
from jangle.models import LanguageTag
from translator.models import GoogleLanguage


class SimpleLangSerializer(s.ModelSerializer):
    class Meta:
        fields = ["description", "text"]
        model = LanguageTag


class SimpleGoogleLangSerializer(s.ModelSerializer):
    lang = s.StringRelatedField(read_only=True)

    class Meta:
        fields = ["description", "lang"]
        model = GoogleLanguage
