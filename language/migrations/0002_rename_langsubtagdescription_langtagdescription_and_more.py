# Generated by Django 4.1.1 on 2022-10-22 05:06

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("language", "0001_initial"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="LangSubtagDescription",
            new_name="LangTagDescription",
        ),
        migrations.RenameModel(
            old_name="LangSubtagPrefix",
            new_name="LangTagPrefix",
        ),
        migrations.AlterModelOptions(
            name="langtag",
            options={"verbose_name": "RFC5646 language tag"},
        ),
        migrations.AlterModelOptions(
            name="langtagdescription",
            options={"verbose_name": "language tag description"},
        ),
        migrations.AlterModelOptions(
            name="langtagprefix",
            options={"verbose_name": "language tag prefix"},
        ),
    ]
