from rest_framework import serializers
from maas import models

class FlexNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.FlexNote
        fields = [
            'duration_mode',
            'tone',
            'degree',
            'is_ghosted'
        ]

class LexemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Lexeme
        fields = [] # TODO
