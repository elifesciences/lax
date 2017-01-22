# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('publisher', '0003_auto_20150914_0955'),
    ]

    operations = [
        migrations.AlterField(
            model_name='article',
            name='version',
            field=models.PositiveSmallIntegerField(default=None, help_text=b'The version of the article. Version=None means pre-publication'),
        ),
        migrations.AlterField(
            model_name='historicalarticle',
            name='version',
            field=models.PositiveSmallIntegerField(default=None, help_text=b'The version of the article. Version=None means pre-publication'),
        ),
    ]
