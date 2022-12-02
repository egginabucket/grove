# Generated by Django 4.1.2 on 2022-12-02 17:59

from django.db import migrations, models
import django.db.models.deletion
import maas.music


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("jangle", "0003_alter_ianasubtagdescription_unique_together_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="FlexNote",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "size_mode",
                    models.CharField(
                        choices=[
                            ("1", "large (whole) note"),
                            ("4", "medium (1/4) note"),
                            (".", "small (staccato 1/4) note"),
                        ],
                        max_length=1,
                    ),
                ),
                (
                    "tone",
                    models.CharField(
                        choices=[
                            ("N", "nucleus"),
                            ("U", "upper satellite"),
                            ("L", "lower satellite"),
                        ],
                        max_length=1,
                    ),
                ),
                ("degree", models.SmallIntegerField(default=0)),
                ("is_ghosted", models.BooleanField(default=False)),
            ],
            bases=(models.Model, maas.music.AbstractFlexNote),
        ),
        migrations.CreateModel(
            name="Lexeme",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("comment", models.TextField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name="LexemeTranslation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("word", models.CharField(max_length=254)),
                (
                    "lang",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="jangle.languagetag",
                    ),
                ),
                (
                    "lexeme",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="translations",
                        to="maas.lexeme",
                    ),
                ),
            ],
            options={
                "unique_together": {("lexeme", "lang"), ("word", "lang")},
            },
        ),
        migrations.CreateModel(
            name="LexemeFlexNote",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("index", models.PositiveSmallIntegerField()),
                (
                    "flex_note",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lexeme_through",
                        to="maas.flexnote",
                    ),
                ),
                (
                    "lexeme",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="flex_note_through",
                        to="maas.lexeme",
                    ),
                ),
            ],
            options={
                "ordering": ["lexeme", "index"],
                "unique_together": {("lexeme", "index")},
            },
        ),
    ]
