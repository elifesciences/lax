# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import autoslug.fields
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Article',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('doi', models.CharField(help_text=b"Article's unique ID in the wider world. All articles must have one as an absolute minimum", unique=True, max_length=255)),
                ('title', models.CharField(help_text=b'The title of the article', max_length=255, null=True, blank=True)),
                ('slug', autoslug.fields.AutoSlugField(populate_from=b'title', editable=False, blank=True, help_text=b'A friendlier version of the title for machines', null=True)),
                ('version', models.PositiveSmallIntegerField(default=1, help_text=b'The version of the article. All articles have at least a version 1')),
                ('volume', models.PositiveSmallIntegerField(null=True, blank=True)),
                ('status', models.CharField(blank=True, max_length=3, null=True, choices=[(b'poa', b'POA'), (b'vor', b'VOR')])),
                ('website_path', models.CharField(max_length=50)),
                ('datetime_submitted', models.DateTimeField(help_text=b'Date author submitted article', null=True, blank=True)),
                ('datetime_accepted', models.DateTimeField(help_text=b'Date article accepted for publication', null=True, blank=True)),
                ('datetime_published', models.DateTimeField(help_text=b'Date article first appeared on website', null=True, blank=True)),
                ('datetime_record_created', models.DateTimeField(help_text=b'Date this article was created', auto_now_add=True)),
                ('datetime_record_updated', models.DateTimeField(help_text=b'Date this article was updated', auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='ArticleAttribute',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.CharField(max_length=255)),
                ('datetime_record_created', models.DateTimeField(help_text=b'Date this attribute was created', auto_now_add=True)),
                ('datetime_record_updated', models.DateTimeField(help_text=b'Date this attribute was updated', auto_now=True)),
                ('article', models.ForeignKey(to='publisher.Article')),
            ],
        ),
        migrations.CreateModel(
            name='AttributeType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('slug', autoslug.fields.AutoSlugField(populate_from=b'name', editable=False)),
                ('type', models.CharField(max_length=10, choices=[(b'char', b'String'), (b'int', b'Integer'), (b'float', b'Float'), (b'date', b'Date')])),
                ('description', models.TextField(null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='HistoricalArticle',
            fields=[
                ('id', models.IntegerField(verbose_name='ID', db_index=True, auto_created=True, blank=True)),
                ('doi', models.CharField(help_text=b"Article's unique ID in the wider world. All articles must have one as an absolute minimum", max_length=255, db_index=True)),
                ('title', models.CharField(help_text=b'The title of the article', max_length=255, null=True, blank=True)),
                ('slug', autoslug.fields.AutoSlugField(populate_from=b'title', editable=False, blank=True, help_text=b'A friendlier version of the title for machines', null=True)),
                ('version', models.PositiveSmallIntegerField(default=1, help_text=b'The version of the article. All articles have at least a version 1')),
                ('volume', models.PositiveSmallIntegerField(null=True, blank=True)),
                ('status', models.CharField(blank=True, max_length=3, null=True, choices=[(b'poa', b'POA'), (b'vor', b'VOR')])),
                ('website_path', models.CharField(max_length=50)),
                ('datetime_submitted', models.DateTimeField(help_text=b'Date author submitted article', null=True, blank=True)),
                ('datetime_accepted', models.DateTimeField(help_text=b'Date article accepted for publication', null=True, blank=True)),
                ('datetime_published', models.DateTimeField(help_text=b'Date article first appeared on website', null=True, blank=True)),
                ('datetime_record_created', models.DateTimeField(help_text=b'Date this article was created', editable=False, blank=True)),
                ('datetime_record_updated', models.DateTimeField(help_text=b'Date this article was updated', editable=False, blank=True)),
                ('history_id', models.AutoField(serialize=False, primary_key=True)),
                ('history_date', models.DateTimeField()),
                ('history_type', models.CharField(max_length=1, choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')])),
                ('history_user', models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
                'verbose_name': 'historical article',
            },
        ),
        migrations.CreateModel(
            name='HistoricalArticleAttribute',
            fields=[
                ('id', models.IntegerField(verbose_name='ID', db_index=True, auto_created=True, blank=True)),
                ('value', models.CharField(max_length=255)),
                ('datetime_record_created', models.DateTimeField(help_text=b'Date this attribute was created', editable=False, blank=True)),
                ('datetime_record_updated', models.DateTimeField(help_text=b'Date this attribute was updated', editable=False, blank=True)),
                ('history_id', models.AutoField(serialize=False, primary_key=True)),
                ('history_date', models.DateTimeField()),
                ('history_type', models.CharField(max_length=1, choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')])),
                ('article', models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.DO_NOTHING, db_constraint=False, blank=True, to='publisher.Article', null=True)),
                ('history_user', models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, null=True)),
                ('key', models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.DO_NOTHING, db_constraint=False, blank=True, to='publisher.AttributeType', null=True)),
            ],
            options={
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
                'verbose_name': 'historical article attribute',
            },
        ),
        migrations.CreateModel(
            name='Journal',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text=b'Name of the journal.', max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Publisher',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
            ],
        ),
        migrations.AddField(
            model_name='journal',
            name='publisher',
            field=models.ForeignKey(to='publisher.Publisher', help_text=b"A publisher may have many journals. A journal doesn't necessarily need a Publisher.", null=True),
        ),
        migrations.AddField(
            model_name='historicalarticle',
            name='journal',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.DO_NOTHING, db_constraint=False, blank=True, to='publisher.Journal', null=True),
        ),
        migrations.AddField(
            model_name='articleattribute',
            name='key',
            field=models.ForeignKey(to='publisher.AttributeType'),
        ),
        migrations.AddField(
            model_name='article',
            name='journal',
            field=models.ForeignKey(to='publisher.Journal'),
        ),
    ]
