# -*- coding: utf-8 -*-


from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("publisher", "0004_auto_20150917_0832")]

    operations = [
        migrations.AlterModelOptions(
            name="article", options={"ordering": ("version",)}
        ),
        migrations.AlterUniqueTogether(
            name="articleattribute", unique_together=set([("article", "key")])
        ),
    ]
