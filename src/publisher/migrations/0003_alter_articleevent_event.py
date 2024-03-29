# Generated by Django 3.2.19 on 2023-05-23 07:17

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("publisher", "0002_auto_20210701_0651"),
    ]

    operations = [
        migrations.AlterField(
            model_name="articleevent",
            name="event",
            field=models.CharField(
                choices=[
                    ("date-reviewed-preprint", "reviewed-preprint version published"),
                    ("date-preprint", "preprint published"),
                    ("date-sent-for-peer-review", "sent for peer review"),
                    ("date-qc", "quality check date"),
                    ("date-decision", "decision date"),
                    ("date-xml-received", "received date (XML)"),
                    ("date-xml-accepted", "accepted date (XML)"),
                    ("datetime-action-ingest", "'ingest' event"),
                    ("datetime-action-publish", "'publish' event"),
                ],
                max_length=50,
            ),
        ),
    ]
