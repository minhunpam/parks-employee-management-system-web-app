import { csrfToken } from "../common.js";

const employeeRegistrationPage = document.querySelector("#employee-registration-page");
const employeeDashboardUrl = employeeRegistrationPage.dataset.employeeDashboardUrl;
const employeeRegistrationUrl = employeeRegistrationPage.dataset.employeeRegistrationUrl;

const form = document.querySelector("#employee-registration-form");

const email = document.querySelector("#email");
const employmentStartDate = document.querySelector("#employment-start-date");
const employmentEndDate = document.querySelector("#employment-end-date");

const cancelButton = document.querySelector("#cancel-registration-button");
const employeeRegistrationStatus = document.querySelector("#employee-registration-status");

const today = new Date();

employmentStartDate.addEventListener("change", () => {
  if (new Date(employmentStartDate.value) > today)
  {
    employmentStartDate.setCustomValidity("Start date cannot be in the future");
    employmentStartDate.value = "";
  }
  else if (
    employmentEndDate.value
    && new Date(employmentEndDate.value) === new Date(employmentStartDate.value))
  {
    employmentStartDate.setCustomValidity("Start date cannot be the same as end date");
    employmentStartDate.value = "";
  }
  else {
    employmentStartDate.setCustomValidity("");
  }

  employmentStartDate.reportValidity();
});

employmentEndDate.addEventListener("change", () => {
  if (new Date(employmentEndDate.value) < today)
  {
    employmentEndDate.setCustomValidity("End date cannot be in the past");
    employmentEndDate.value = "";
  }
  else if (
    employmentStartDate.value
    && new Date(employmentEndDate.value) === new Date(employmentStartDate.value))
  {
    employmentEndDate.setCustomValidity("Start date cannot be the same as end date");
    employmentEndDate.value = "";
  }
  else {
    employmentEndDate.setCustomValidity("");
  }

  employmentEndDate.reportValidity();
});

cancelButton.addEventListener("click", () => {
  window.location.assign(employeeDashboardUrl);
});

async function registerEmployee(payload) {
  const response = await fetch(employeeRegistrationUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken(),
    },
    body: JSON.stringify(payload),
  });

  return {
    original_response: response,
    result: await response.json(),
  };
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const payload = Object.fromEntries(new FormData(form));
  let result;

  const confirmed = window.confirm(
    "Are you sure every fields were correctly entered?\n\n"
    + "If previous months are imported, they will use the registered workday value. "
    + "Later schedule changes will not affect those imported months."
  );
  if (!confirmed) {
    return;
  }

  try {
    result = await registerEmployee(payload);
    if (result.original_response.status === 200) {
      employeeRegistrationStatus.textContent = result.result.message;
      form.reset();
    }

    const errorObj = result.result.error;

    if (errorObj && errorObj.email) {
      email.setCustomValidity(errorObj.email.join(" "));
      email.reportValidity();
    }

  } catch (error) {
    employeeRegistrationStatus.textContent = "Something wrong happened and the developer has caught this!";
  }
});
