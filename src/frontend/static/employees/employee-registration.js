import { csrfToken } from "../common.js";

const employeeDashboardPage = document.querySelector("#employee-dashboard-page");
const employeeRegistrationUrl = employeeDashboardPage.dataset.employeeRegistrationUrl;

const registerEmployeeButton = document.querySelector("#register-employee-button");
const modal = document.querySelector("#employee-registration-modal");
const form = document.querySelector("#employee-registration-form");
const cancelButton = document.querySelector("#cancel-registration-button");

const employmentStartDate = document.querySelector("#employment-start-date");
const employmentEndDate = document.querySelector("#employment-end-date");

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

registerEmployeeButton.addEventListener("click", () => {
  modal.showModal();
});

cancelButton.addEventListener("click", () => {
  modal.close();
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
  
  try {
    result = await registerEmployee(payload);
    console.log(result.result.message);
  } catch (error) {
    console.log(error);
    return;
  }

  modal.close();
  form.reset();
});
