# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-03-21 02:26
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("publisher", "0001_squashed_0040_auto_20170315_0459")]

    operations = [
        migrations.AlterField(
            model_name="article",
            name="doi",
            field=models.CharField(
                help_text="Article's unique ID in the wider world. All articles must have one as an absolute minimum",
                max_length=255,
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name="articlefragment",
            name="datetime_record_created",
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
