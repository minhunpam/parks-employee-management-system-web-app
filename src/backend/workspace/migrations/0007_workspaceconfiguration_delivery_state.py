from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("workspace", "0006_workspaceconfiguration_manager_recipients"),
    ]

    operations = [
        migrations.AddField(
            model_name="workspaceconfiguration",
            name="delivery_state",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
