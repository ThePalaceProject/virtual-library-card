# Generated by Django 4.2.15 on 2025-04-24 18:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        (
            "virtuallibrarycard",
            "0001_squashed_0092_remove_library_sequence_down_and_more",
        ),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="library",
            options={"ordering": ["name"], "verbose_name_plural": "libraries"},
        ),
        migrations.RemoveField(
            model_name="customuser",
            name="city",
        ),
        migrations.RemoveField(
            model_name="customuser",
            name="country_code",
        ),
        migrations.RemoveField(
            model_name="customuser",
            name="place",
        ),
        migrations.RemoveField(
            model_name="customuser",
            name="street_address_line1",
        ),
        migrations.RemoveField(
            model_name="customuser",
            name="street_address_line2",
        ),
        migrations.RemoveField(
            model_name="customuser",
            name="zip",
        ),
        migrations.RemoveField(
            model_name="library",
            name="patron_address_mandatory",
        ),
    ]
