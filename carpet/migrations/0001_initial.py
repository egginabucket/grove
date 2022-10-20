# Generated by Django 4.1.1 on 2022-10-15 19:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("maas", "0001_initial"),
        ("language", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Phrase",
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
                    "pitch_change",
                    models.CharField(
                        choices=[("+", "up"), ("-", "down"), ("@", "last")],
                        max_length=1,
                        null=True,
                    ),
                ),
                ("multiplier", models.PositiveSmallIntegerField(default=1)),
                ("count", models.PositiveSmallIntegerField(null=True)),
                (
                    "suffix",
                    models.CharField(
                        choices=[("?", "question"), ("!", "not")],
                        max_length=1,
                        null=True,
                    ),
                ),
                (
                    "lexeme",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="maas.lexeme",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Term",
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
                ("term", models.CharField(max_length=254)),
                ("source_file", models.CharField(max_length=254, null=True)),
                (
                    "language",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="language.language",
                    ),
                ),
                (
                    "phrase",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="defined_terms",
                        to="carpet.phrase",
                    ),
                ),
                (
                    "pos_tag",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="language.postag",
                    ),
                ),
            ],
            options={
                "unique_together": {("term", "language", "pos_tag")},
            },
        ),
        migrations.CreateModel(
            name="PhraseComposition",
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
                ("index", models.SmallIntegerField()),
                ("has_braces", models.BooleanField(default=False)),
                (
                    "child",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="parent_rels",
                        to="carpet.phrase",
                    ),
                ),
                (
                    "parent",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="child_rels",
                        to="carpet.phrase",
                    ),
                ),
            ],
            options={
                "unique_together": {("parent", "index")},
            },
        ),
    ]
