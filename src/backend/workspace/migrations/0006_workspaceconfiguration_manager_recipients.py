from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workspace", "0005_alter_workspaceconfiguration_period_month_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="workspaceconfiguration",
            name="manager_recipients",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
