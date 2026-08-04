from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workspace", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="workspaceconfiguration",
            name="spreadsheet_id",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
