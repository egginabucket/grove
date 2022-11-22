from jangle.models import LanguageTag

from maas.models import Lexeme, LexemeTranslation

EN = LanguageTag.objects.get_from_str("en")


def lexeme_from_en(word: str) -> Lexeme:
    return LexemeTranslation.objects.get(lang=EN, word=word).lexeme
