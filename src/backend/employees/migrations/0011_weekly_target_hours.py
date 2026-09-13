from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations, models
from django.db.models import Q
from django.core.validators import MaxValueValidator, MinValueValidator


def backfill_weekly_target_hours(apps, schema_editor):
    Employee = apps.get_model("employees", "Employee")
    for employee in Employee.objects.all().iterator():
        employee.weekly_target_hours = (
            employee.monthly_target_hours * Decimal("3") / Decimal("13")
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        employee.save(update_fields=["weekly_target_hours"])


def reverse_backfill(apps, schema_editor):
    # The original monthly value is intentionally preserved by the forward
    # migration; there is no lossy reverse transformation to perform.
    pass


class Migration(migrations.Migration):
    dependencies = [("employees", "0010_alter_employee_email_and_more")]

    operations = [
        migrations.AddField(
            model_name="employee",
            name="weekly_target_hours",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("40.00"),
                max_digits=5,
                validators=[
                    MinValueValidator(Decimal("20.00")),
                    MaxValueValidator(Decimal("40.00")),
                ],
            ),
        ),
        migrations.RunPython(backfill_weekly_target_hours, reverse_backfill),
        migrations.AlterField(
            model_name="employee",
            name="work_days_per_week",
            field=models.PositiveIntegerField(
                default=5,
                validators=[MinValueValidator(1), MaxValueValidator(7)],
            ),
        ),
        migrations.AddConstraint(
            model_name="employee",
            constraint=models.CheckConstraint(
                condition=Q(work_days_per_week__gte=1, work_days_per_week__lte=7),
                name="work_days_per_week_range",
            ),
        ),
        migrations.AddConstraint(
            model_name="employee",
            constraint=models.CheckConstraint(
                condition=Q(weekly_target_hours__gte=Decimal("20.00"), weekly_target_hours__lte=Decimal("40.00")),
                name="weekly_target_hours_range",
            ),
        ),
    ]
