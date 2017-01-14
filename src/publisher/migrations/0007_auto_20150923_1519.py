# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('publisher', '0006_auto_20150922_1621'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attributetype',
            name='type',
            field=models.CharField(default=b'char', max_length=10, choices=[(b'char', b'String'), (b'int', b'Integer'), (b'float', b'Float'), (b'date', b'Date')]),
        ),
    ]
