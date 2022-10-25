# Generated by Django 4.1.2 on 2022-10-25 16:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("language", "0003_rename_lang_isolang_rename_langname_isolangname_and_more"),
        ("carpet", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="term",
            old_name="language",
            new_name="iso_lang",
        ),
        migrations.AlterUniqueTogether(
            name="term",
            unique_together={("lemma", "iso_lang", "pos_tag")},
        ),
    ]