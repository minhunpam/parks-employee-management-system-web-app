import { csrfToken } from "../common.js";

const entryPage = document.querySelector("#entry-page");
const csvImportUrl_Check = entryPage.dataset.csvImportUrlCheck;
const csvImportUrl_Import = entryPage.dataset.csvImportUrlImport;
const connectUrl = entryPage.dataset.connectUrl;

const importCsvButton_Check = document.querySelector("#import-csv-button-check");
const importCsvButton_Import = document.querySelector("#import-csv-button-import");
const importCsvStatus = document.querySelector("#import-csv-status-check");
const reconnectGoogle = document.querySelector("#reconnect-google");

const rootFolderLink = document.querySelector("#root-folder-link");
const pipelineContainer = document.querySelector("#pipeline-container");
const pipelinePhases = pipelineContainer.children

const readySignal = document.querySelector("#ready-signal");

function signalPipelinePhases(phase) {
  for (let phase_index = 0; phase_index < pipelinePhases.length; ++phase_index) {
    if (phase_index === phase) {
      pipelinePhases[phase].classList.remove("border-[#cccccc]");
      pipelinePhases[phase].classList.add("border-[#76b900]");
      continue;
    }

    pipelinePhases[phase_index].classList.remove("border-[#76b900]");
    pipelinePhases[phase_index].classList.add("border-[#cccccc]");
  }
}

function setRootFolderAttention(isAttentionNeeded) {
  rootFolderLink?.classList.toggle("folder-attention", isAttentionNeeded);
}

importCsvButton_Check.addEventListener("click", async () => {
  if (!importCsvButton_Import.hidden) {
    importCsvButton_Import.hidden = true;
  }

  signalPipelinePhases(0);
  if (readySignal.classList.contains("border-[#76b900]") && readySignal.classList.contains("text-[#76b900]")) {
    readySignal.classList.remove("border-[#76b900]", "text-[#76b900]");
    readySignal.classList.add("border-[#cccccc]", "text-[#757575]");
  }
  
  importCsvButton_Check.disabled = true;
  importCsvStatus.textContent = "Checking the previous month's import folder…";

  try {
    const response = await fetch(csvImportUrl_Check, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken(),
      },
    });
    const result = await response.json();

    if (result.code === "google_reconnect_required" || response.status === 401) {
      importCsvStatus.textContent = result.error || "Please reconnect Google.";
      reconnectGoogle.href = connectUrl;
      reconnectGoogle.hidden = false;
    }
    else if (result.status === "awaiting_upload") {
      importCsvStatus.textContent = result.message;
      setRootFolderAttention(true);
    }
    else if (result.status === "invalid_files") {
      importCsvStatus.textContent = `${result.message} Invalid files: ${result.invalid_files.join(", ")}`;
      setRootFolderAttention(false);
    }
    else if (result.status === "ready") {
      importCsvStatus.textContent = `${result.files.length} CSV file(s) found in ${result.folder.name}.`;
      importCsvButton_Import.hidden = false;

      setRootFolderAttention(false);
    }
    else {
      importCsvStatus.textContent = result.error || "CSV import could not be prepared.";
    }
  } catch (error) {
    importCsvStatus.textContent = "The CSV import check failed. Please try again.";
  } finally {
    importCsvButton_Check.disabled = false;
  }
});

importCsvButton_Import.addEventListener("click", async () => {

  importCsvButton_Check.disabled = true;
  importCsvButton_Import.disabled = true;
  signalPipelinePhases(1);
  if (readySignal.classList.contains("border-[#76b900]") && readySignal.classList.contains("text-[#76b900]")) {
    readySignal.classList.remove("border-[#76b900]", "text-[#76b900]");
    readySignal.classList.add("border-[#cccccc]", "text-[#757575]");
  }
  
  const response = await fetch(csvImportUrl_Import, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken(),
    },
  });

  const result = await response.json();

  if (result.code === "google_reconnect_required" || response.status === 401) {
    importCsvStatus.textContent = result.error || "Please reconnect Google.";
    reconnectGoogle.href = connectUrl;
    reconnectGoogle.hidden = false;
    return;
  }

  if (result.errors) {
    importCsvStatus.textContent = "";
    for (const error of result.errors) {
      importCsvStatus.append(error.error);
    }
  }
  
  importCsvButton_Import.disabled = false;
  importCsvButton_Check.disabled = false;
  
  if (response.status === 200) {
    importCsvStatus.textContent = result.message;
    signalPipelinePhases(2);
    readySignal.classList.remove("border-[#cccccc]", "text-[#757575]");
    readySignal.classList.add("border-[#76b900]", "text-[#76b900]");
  }
});

rootFolderLink.addEventListener("click", () => {
  setRootFolderAttention(false);
});

