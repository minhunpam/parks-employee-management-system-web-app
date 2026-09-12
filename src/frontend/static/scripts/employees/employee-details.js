import { csrfToken } from "../common.js";

const page = document.querySelector("#employee-details-page");
const detailsUrl = page.dataset.detailsUrl;
const dashboardUrl = page.dataset.dashboardUrl;

const form = document.querySelector("#employee-details-form");
const status = document.querySelector("#employee-details-status");
const saveChangesButton = document.querySelector("#save-changes-button");
const cancelButton = document.querySelector("#cancel-details-button");
const archiveButton = document.querySelector("#archive-employee-button");
const workingStatus = document.querySelector("#working-status");

if (workingStatus.value === "archived") {
  archiveButton.hidden = true;
}

cancelButton.addEventListener("click", () => {
  window.location.assign(dashboardUrl);
});

async function updateEmployee(payload) {
  const response = await fetch(detailsUrl, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken(),
    },
    body: JSON.stringify(payload),
  });

  return {
    original_response: response,
    result: await response.json()
  };
}

function showErrors(error) {
  const messages = Object.values(error ?? {}).flat();
  status.textContent = messages.length
    ? messages.join(" ")
    : "Could not save the employee details.";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  status.textContent = "Saving changes…";

  try {
    const { original_response, result } = await updateEmployee(Object.fromEntries(new FormData(form)));

    if (!original_response.ok) {
      showErrors(result.error);
      return;
    }

    status.textContent = result.message;
  } catch (error) {
    console.error(error);
    status.textContent = "Something went wrong. Please try again.";
  }
});

archiveButton.addEventListener("click", async () => {
  const confirmed = window.confirm(
    "Archive this employee? Their history will be preserved and their employment end date will be set to today."
  );

  if (!confirmed) {
    return;
  }

  archiveButton.disabled = true;
  status.textContent = "Archiving employee…";

  try {
    const { original_response, result } = await updateEmployee({ action: "archive" });

    if (!original_response.ok) {
      showErrors(result.error);
      archiveButton.disabled = false;
      return;
    }

    window.location.assign(dashboardUrl);
  } catch (error) {
    console.error(error);
    status.textContent = "Something went wrong. Please try again.";
    archiveButton.disabled = false;
  }
});

document.querySelectorAll(".form-field").forEach((field) => {
  field.addEventListener("input", checkForInputFieldChanges);
  field.addEventListener("change", checkForInputFieldChanges);
});

function checkForInputFieldChanges() {
  const hasChanges = [...document.querySelectorAll(".form-field")].some((field) => field.dataset.originalValue !== field.value);
  saveChangesButton.toggleAttribute("disabled", !hasChanges);
}
