# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields


class Migration(migrations.Migration):

    dependencies = [("publisher", "0002_auto_20150806_2254")]

    operations = [
        migrations.AlterField(
            model_name="article",
            name="doi",
            field=models.CharField(
                help_text=b"Article's unique ID in the wider world. All articles must have one as an absolute minimum",
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="article",
            name="slug",
            field=autoslug.fields.AutoSlugField(
                populate_from=b"title",
                editable=False,
                always_update=True,
                blank=True,
                help_text=b"A friendlier version of the title for machines",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="article",
            name="version",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text=b"The version of the article. Version=0 means pre-publication",
            ),
        ),
        migrations.AlterField(
            model_name="attributetype",
            name="slug",
            field=autoslug.fields.AutoSlugField(
                always_update=True, populate_from=b"name", editable=False
            ),
        ),
        migrations.AlterField(
            model_name="historicalarticle",
            name="doi",
            field=models.CharField(
                help_text=b"Article's unique ID in the wider world. All articles must have one as an absolute minimum",
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="historicalarticle",
            name="slug",
            field=autoslug.fields.AutoSlugField(
                populate_from=b"title",
                editable=False,
                always_update=True,
                blank=True,
                help_text=b"A friendlier version of the title for machines",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="historicalarticle",
            name="version",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text=b"The version of the article. Version=0 means pre-publication",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="article", unique_together=set([("doi", "version")])
        ),
    ]
