# Generated by Django 4.1.1 on 2022-10-04 02:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("moss", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PosTag",
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
                ("abbr", models.CharField(max_length=5, verbose_name="abbreviation")),
                ("name", models.CharField(max_length=126)),
                (
                    "category",
                    models.SmallIntegerField(
                        choices=[(0, "Open class"), (1, "Closed class"), (2, "Other")]
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="definition",
            name="pos_tag",
            field=models.ForeignKey(
                default=None,
                on_delete=django.db.models.deletion.PROTECT,
                to="moss.postag",
            ),
            preserve_default=False,
        ),
    ]
