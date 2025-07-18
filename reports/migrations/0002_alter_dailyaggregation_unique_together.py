# Generated by Django 4.2.16 on 2025-01-24 03:05

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        # ("course", "0007_remove_course_program_remove_upload_file_and_more"),
        ("reports", "0001_initial"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="dailyaggregation",
            unique_together={
                (
                    "user",
                    "date",
                    "type_of_aggregation",
                    "course",
                    "reference_id",
                    "resource_name",
                )
            },
        ),
    ]
