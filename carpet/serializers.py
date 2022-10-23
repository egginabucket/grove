from rest_framework import serializers
from carpet import models

class PhraseSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Phrase
        fields = [ # TODO
            'pitch_change',
            'multiplier',
            'count',
            'suffix',
        ]

class TermSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Term
        fields = [
            'lemma'
        ]