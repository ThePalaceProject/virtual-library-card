import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    # Re-introduces a patron ZIP code, which was dropped along with the rest of the
    # physical address in 0093. The column stays nullable because whether a ZIP is
    # required is decided per library at form level (Library.patron_zip_collection),
    # so admin- and bulk-created users must still be saveable without one.
    #
    # choices/verbose_name are absent by design: the app's custom makemigrations
    # command strips decorative attributes from migrations.

    dependencies = [
        ("virtuallibrarycard", "0094_remove_library_uuid"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="zip",
            field=models.CharField(
                blank=True,
                max_length=5,
                null=True,
                validators=[
                    django.core.validators.RegexValidator(
                        message="Enter a 5-digit ZIP code.", regex="^\\d{5}$"
                    )
                ],
            ),
        ),
        migrations.AddField(
            model_name="library",
            name="patron_zip_collection",
            field=models.CharField(default="off", max_length=16),
        ),
    ]
