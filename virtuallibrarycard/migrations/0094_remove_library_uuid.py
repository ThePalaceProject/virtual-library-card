# Generated by Django 4.2.15 on 2025-04-24 18:22

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        (
            "virtuallibrarycard",
            "0093_alter_library_options_remove_customuser_city_and_more",
        ),
    ]

    operations = [
        migrations.RemoveField(
            model_name="library",
            name="uuid",
        ),
    ]
