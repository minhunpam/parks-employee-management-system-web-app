from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("employees", "0007_employeemonth_unique_employee_year_month"),
    ]

    operations = [
        migrations.AlterField(
            model_name="employeemonth",
            name="opening_hour_account_balance",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8),
        ),
        migrations.AlterField(
            model_name="employeemonth",
            name="target_working_hours",
            field=models.DecimalField(decimal_places=2, max_digits=8),
        ),
        migrations.AlterField(
            model_name="employeemonth",
            name="paid_absence_hours",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8),
        ),
        migrations.AlterField(
            model_name="employeemonth",
            name="worked_hours",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8),
        ),
        migrations.AlterField(
            model_name="employeemonth",
            name="credited_working_hours",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8),
        ),
        migrations.AlterField(
            model_name="employeemonth",
            name="hour_difference",
            field=models.DecimalField(decimal_places=2, max_digits=8),
        ),
        migrations.AlterField(
            model_name="employeemonth",
            name="closing_hour_account_balance",
            field=models.DecimalField(decimal_places=2, max_digits=8),
        ),
    ]
