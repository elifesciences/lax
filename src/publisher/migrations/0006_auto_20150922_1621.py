# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('publisher', '0005_auto_20150922_1307'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='attributetype',
            name='slug',
        ),
        migrations.AlterField(
            model_name='attributetype',
            name='name',
            field=models.SlugField(),
        ),
    ]
