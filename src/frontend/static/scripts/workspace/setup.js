import { csrfToken } from "../common.js";

const page = document.querySelector("#setup-page");
const saveUrl = page.dataset.saveUrl;
const successfulRedirectUrl = page.dataset.successfulRedirectUrl;
const connectUrl = page.dataset.connectUrl;

const form = document.querySelector("#setup-form");
const rootFolderInput = document.querySelector("#root-folder-id");
const spreadsheetInput = document.querySelector("#spreadsheet-id");
const periodMonthInput = document.querySelector("#period-month");
const periodYearInput = document.querySelector("#period-year");

const setupStatus = document.querySelector("#setup-status");
const reconnectGoogle = document.querySelector("#reconnect-google");
const confirmationDialog = document.querySelector("#workspace-confirmation-dialog");
const confirmationMessage = document.querySelector("#workspace-confirmation-message");
const confirmationInput = document.querySelector("#workspace-confirmation-input");

const sessionStorageDraftKey = "workspace-setup-draft";

function saveDraft() {
    sessionStorage.setItem(sessionStorageDraftKey, JSON.stringify({
        root_folder_id: rootFolderInput.value,
        spreadsheet_id: spreadsheetInput.value,
        period_month: periodMonthInput.value,
        period_year: periodYearInput.value,
    }));
}

function restoreDraft() {
    const draft = JSON.parse(sessionStorage.getItem(sessionStorageDraftKey) || "null");

    if (draft) {
        rootFolderInput.value = draft.root_folder_id || "";
        spreadsheetInput.value = draft.spreadsheet_id || "";
        periodMonthInput.value = draft.period_month || "";
        periodYearInput.value = draft.period_year || "";
    }
}

restoreDraft();

function showWorkspaceConfirmation(confirmationPhrase) {
  return new Promise((resolve) => {
    
    confirmationMessage.textContent = "Type ";
    const code = document.createElement("code");
    code.classList.add(
      "border",
      "border-[#cccccc]",
      "bg-[#f7f7f7]",
      "px-1",
      "py-0.5",
      "font-bold",
      "text-[#1a1a1a]",
    );
    
    code.textContent = confirmationPhrase;
    confirmationMessage.append(code, " to confirm this change.");

    confirmationInput.value = "";
    confirmationDialog.returnValue = "cancel";

    const handleClose = () => {
      confirmationDialog.removeEventListener("close", handleClose);
      document.body.classList.remove("overflow-hidden");
      
      resolve(
          confirmationDialog.returnValue === "confirm"
              ? confirmationInput.value
              : null,
      );
    };

    confirmationDialog.addEventListener("close", handleClose);
    confirmationDialog.showModal();
    confirmationInput.focus();
    document.body.classList.add("overflow-hidden");
  });
}


async function saveSetup(payload) {
    const response = await fetch(saveUrl, {
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
    setupStatus.textContent = "Checking Google resources…";

    const payload = Object.fromEntries(new FormData(form));  
    let result;

    try {
      result = await saveSetup(payload);

      if (result.result.requires_confirmation) {
          const confirmation = await showWorkspaceConfirmation(result.result.confirmation_phrase);
          if (confirmation === null) {
              setupStatus.textContent = "Configuration change cancelled.";
              return;
          }

          payload.confirmation = confirmation;
          result = await saveSetup(payload);
      }
      
      if (result.result.code === "google_reconnect_required" || result.original_response.status === 401) {
          setupStatus.textContent = result.result.error || "Please reconnect Google.";
  
          saveDraft();
          
          reconnectGoogle.href = connectUrl;
          reconnectGoogle.hidden = false;
          return;
      }

      setupStatus.textContent = result.original_response.ok
          ? "Workspace configuration saved."
          : (result.result.error || "Setup could not be saved.");

      if (result.original_response.ok) {
          window.location.assign(successfulRedirectUrl);
      }

    } catch (error) {
        setupStatus.textContent = "Setup could not be saved. Please try again.";
    }
});
