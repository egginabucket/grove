# Generated by Django 4.1.2 on 2022-12-02 17:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("maas", "0001_initial"),
        ("carpet", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="phrase",
            name="lexeme",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.CASCADE, to="maas.lexeme"
            ),
        ),
        migrations.AlterUniqueTogether(
            name="synsetdef",
            unique_together={("pos", "wn_offset")},
        ),
        migrations.AlterUniqueTogether(
            name="phrasecomposition",
            unique_together={("parent", "index")},
        ),
    ]
