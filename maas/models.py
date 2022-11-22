from django.db import models
from jangle.models import LanguageTag
from maas.music import FLEX_NOTE_RE, AbstractFlexNote, Tone, DurationMode


class FlexNote(models.Model, AbstractFlexNote):
    duration_mode = models.CharField(
        choices=DurationMode.choices, max_length=1
    )
    tone = models.CharField(choices=Tone.choices, max_length=1)
    degree = models.SmallIntegerField(default=0)
    is_ghosted = models.BooleanField(default=False)

    def __str__(self):
        return AbstractFlexNote.__str__(self)


class Lexeme(models.Model):
    translations: "models.manager.RelatedManager[LexemeTranslation]"
    comment = models.TextField(null=True)
    # flex_notes = models.ManyToManyField(FlexNote, through='LexemeFlexNote')

    def create_flex_notes(self, string: str):
        def generate_flex_notes():
            for match in FLEX_NOTE_RE.finditer(string):
                flex_note = FlexNote()
                flex_note.from_match(match)
                yield flex_note

        flex_notes = FlexNote.objects.bulk_create(generate_flex_notes())
        LexemeFlexNote.objects.bulk_create(
            LexemeFlexNote(
                flex_note=flex_note,
                index=i,
                lexeme=self,
            )
            for i, flex_note in enumerate(flex_notes)
        )

    def get_flex_notes(self) -> list[FlexNote]:
        return [
            rel.flex_note for rel in self.flex_note_through.order_by("index")  # type: ignore
        ]

    def translate(self, lang: LanguageTag) -> str:
        return self.translations.get(lang=lang).word

    def __str__(self):
        return self.translate(LanguageTag.objects.get_from_str('en'))


class LexemeTranslation(models.Model):
    lexeme = models.ForeignKey(
        Lexeme,
        related_name="translations",
        on_delete=models.CASCADE,
    )
    word = models.CharField(max_length=254)
    lang = models.ForeignKey(
        LanguageTag,
        related_name="+",
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return self.word

    class Meta:
        unique_together = (("word", "lang"), ("lexeme", "lang"))


class LexemeFlexNote(models.Model):
    flex_note = models.OneToOneField(
        FlexNote,
        related_name="lexeme_through",
        on_delete=models.CASCADE,
    )
    lexeme = models.ForeignKey(
        Lexeme,
        related_name="flex_note_through",
        on_delete=models.CASCADE,
    )
    index = models.PositiveSmallIntegerField()

    def __str__(self):
        return f"{str(self.lexeme)}/{self.index}: {self.flex_note}"

    class Meta:
        unique_together = ("lexeme", "index")
        ordering = ["lexeme", "index"]
