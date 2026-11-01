import { syncWorkdayFields } from "../employees/employee-details-state.js";

describe("syncWorkdayFields", () => {
  test("updates persisted values and keeps the registered field disabled", () => {
    document.body.innerHTML = `
      <input id="work-days-per-week" value="4" data-original-value="4">
      <input id="registered-work-days-per-week" value="4" data-original-value="4">
    `;

    syncWorkdayFields({
      work_days_per_week: 5,
      registered_work_days_per_week: 5,
    });

    const workDaysField = document.querySelector("#work-days-per-week");
    const registeredWorkDaysField = document.querySelector("#registered-work-days-per-week");
    expect(workDaysField.value).toBe("5");
    expect(workDaysField.dataset.originalValue).toBe("5");
    expect(registeredWorkDaysField.value).toBe("5");
    expect(registeredWorkDaysField.dataset.originalValue).toBe("5");
    expect(registeredWorkDaysField.disabled).toBe(true);
  });
});
