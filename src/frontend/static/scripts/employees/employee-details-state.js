export function syncWorkdayFields(employee, fields = {}) {
  const workDaysField = fields.workDaysField ?? document.querySelector("#work-days-per-week");
  const registeredWorkDaysField = fields.registeredWorkDaysField ?? document.querySelector("#registered-work-days-per-week");

  workDaysField.value = String(employee.work_days_per_week);
  workDaysField.dataset.originalValue = String(employee.work_days_per_week);
  registeredWorkDaysField.value = String(employee.registered_work_days_per_week);
  registeredWorkDaysField.dataset.originalValue = String(employee.registered_work_days_per_week);
  registeredWorkDaysField.disabled = true;
}
