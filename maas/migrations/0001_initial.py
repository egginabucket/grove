# Generated by Django 4.1.2 on 2022-10-24 23:02

from django.db import migrations, models
import django.db.models.deletion
import maas.flex_notes


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("language", "0001_initial"),
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
                    "duration_mode",
                    models.CharField(
                        choices=[
                            ("1", "1/1 note"),
                            ("4", "1/4 note"),
                            (".", "staccato 1/4 note"),
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
            bases=(models.Model, maas.flex_notes.AbstractFlexNote),
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
                        on_delete=django.db.models.deletion.PROTECT,
                        to="language.lang",
                        verbose_name="language",
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
                "unique_together": {("word", "lang"), ("lexeme", "lang")},
            },
        ),
        migrations.CreateModel(
            name="LexemeFlexNote",
            fields=[
                (
                    "flex_note",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="maas.flexnote",
                    ),
                ),
                ("index", models.PositiveSmallIntegerField()),
                (
                    "lexeme",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="flex_notes",
                        to="maas.lexeme",
                    ),
                ),
            ],
            options={
                "unique_together": {("lexeme", "index")},
            },
            bases=("maas.flexnote",),
        ),
    ]
