import { csrfToken } from "./common.js";

const entryPage = document.querySelector("#entry-page");
const importCsvButton = document.querySelector("#import-csv-button");
const importCsvStatus = document.querySelector("#import-csv-status");
const csvImportUrl = entryPage.dataset.csvImportUrl;

importCsvButton.addEventListener("click", async () => {
  importCsvButton.disabled = true;
  importCsvStatus.textContent = "Checking the previous month's import folder…";

  try {
    const response = await fetch(csvImportUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken(),
      },
    });
    const result = await response.json();

    if (result.status === "awaiting_upload") {
      importCsvStatus.textContent = result.message;
    } else if (result.status === "invalid_files") {
      importCsvStatus.textContent = `${result.message} Invalid files: ${result.invalid_files.join(", ")}`;
    } else if (result.status === "ready") {
      importCsvStatus.textContent = `${result.files.length} CSV file(s) found in ${result.folder.name}.`;
    } else {
      importCsvStatus.textContent = result.error || "CSV import could not be prepared.";
    }
  } catch (error) {
    importCsvStatus.textContent = "The CSV import check failed. Please try again.";
  } finally {
    importCsvButton.disabled = false;
  }
});
