import { csrfToken } from "./common.js";

const entryPage = document.querySelector("#entry-page");
const csvImportUrl_Check = entryPage.dataset.csvImportUrlCheck;
const csvImportUrl_Import = entryPage.dataset.csvImportUrlImport;

const importCsvButton_Check = document.querySelector("#import-csv-button-check");
const importCsvStatus_Check = document.querySelector("#import-csv-status-check");
const importCsvButton_Import = document.querySelector("#import-csv-button-import");

importCsvButton_Check.addEventListener("click", async () => {
  if (!importCsvButton_Import.hidden) {
    importCsvButton_Import.hidden = true;
  }
  
  importCsvButton_Check.disabled = true;
  importCsvStatus_Check.textContent = "Checking the previous month's import folder…";

  try {
    const response = await fetch(csvImportUrl_Check, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken(),
      },
    });
    const result = await response.json();

    if (result.status === "awaiting_upload") {
      importCsvStatus_Check.textContent = result.message;
    } else if (result.status === "invalid_files") {
      importCsvStatus_Check.textContent = `${result.message} Invalid files: ${result.invalid_files.join(", ")}`;
    } else if (result.status === "ready") {
      importCsvStatus_Check.textContent = `${result.files.length} CSV file(s) found in ${result.folder.name}.`;
      importCsvButton_Import.hidden = false;
    } else {
      importCsvStatus_Check.textContent = result.error || "CSV import could not be prepared.";
    }
  } catch (error) {
    importCsvStatus_Check.textContent = "The CSV import check failed. Please try again.";
  } finally {
    importCsvButton_Check.disabled = false;
  }
});

importCsvButton_Import.addEventListener("click", async () => {
  console.log("Importing CSV...");

  importCsvButton_Check.disabled = true;
  importCsvButton_Import.disabled = true;

  const response = await fetch(csvImportUrl_Import, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken(),
    },
  });

  const result = await response.json();
  importCsvButton_Import.disabled = false;
  console.log(result);
  
});
