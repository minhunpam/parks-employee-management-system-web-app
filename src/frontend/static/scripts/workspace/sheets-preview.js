import { csrfToken, htmlInjectionProtection, getDaysInMonth } from "../common.js";

const page = document.querySelector("#sheets-preview-page");
const overviewUrl = page.dataset.overviewUrl;
const refreshUrl = page.dataset.refreshUrl;
const writeUrl = page.dataset.writeUrl;

const state = {
    overview: null,
    selectedEmployee: null,
    filter: "",
    editingEntry: null,
};

const overviewTableHead = document.querySelector("#overview-table-head");
const overviewTableBody = document.querySelector("#overview-table-body");

const employeeSearch = document.querySelector("#employee-search");
const tableStatus = document.querySelector("#table-status");
const syncStatus = document.querySelector("#sync-status");
const externalChangeNotice = document.querySelector("#external-change-notice");
const detailSection = document.querySelector("#employee-detail-section");
const detailHeading = document.querySelector("#employee-detail-heading");
const detailStatus = document.querySelector("#employee-detail-status");
const employeeTableHead = document.querySelector("#employee-table-head");
const employeeTableBody = document.querySelector("#employee-table-body");
const employeeEmpty = document.querySelector("#employee-empty");
const openSheetsLink = document.querySelector("#open-sheets-link");
const openEmployeeSheetLink = document.querySelector("#open-employee-sheet-link");

const dialog = document.querySelector("#entry-dialog");
const entryForm = document.querySelector("#entry-form");
const entryDate = document.querySelector("entry-date");
const entryType = document.querySelector("#entry-type");
const entryStart = document.querySelector("#entry-start");
const entryEnd = document.querySelector("#entry-end");

const entryFormStatus = document.querySelector("#entry-form-status");

function sheetUrl(sheetId) {
  if (!sheetId || sheetId === "preview-spreadsheet") {
    return "#";
  }

  return `https://docs.google.com/spreadsheets/d/${encodeURIComponent(state.overview.spreadsheetId)}/edit#gid=${encodeURIComponent(sheetId)}`;
}

function renderOverview() {
  const headers = state.overview.overview.headers || [];
  const rows = (state.overview.overview.rows || []).filter((row) =>
      !state.filter || String(row.employee).toLowerCase().includes(state.filter.toLowerCase())
  );

  overviewTableHead.innerHTML =
    `<tr>${headers.map((header) =>
      `<th scope="col" class="border-b border-[#cccccc] px-4 py-4 font-bold">${htmlInjectionProtection(header)}</th>`).join("")}
      <th scope="col" class="border-b border-[#cccccc] px-4 py-4 font-bold">Actions</th>
    </tr>`;
  
  overviewTableBody.innerHTML = rows.map((row) =>
    `<tr class="border-b border-[#cccccc] last:border-0 hover:bg-[#f7f7f7]">
        <th scope="row" class="px-4 py-4 font-bold">${htmlInjectionProtection(row.employee)}</th>
        <td class="px-4 py-4">${htmlInjectionProtection(row.target)}</td>
        <td class="px-4 py-4">${htmlInjectionProtection(row.worked)}</td>
        <td class="px-4 py-4">${htmlInjectionProtection(row.difference)}</td>
        <td class="px-4 py-4">${htmlInjectionProtection(row.opening)}</td>
        <td class="px-4 py-4">${htmlInjectionProtection(row.closing)}</td>
        <td class="px-4 py-4">${htmlInjectionProtection(row.vacation)}</td>
        <td class="px-4 py-4 ${row.warnings !== "—" ? "font-bold text-[#df6500]" : "text-[#757575]"}">${htmlInjectionProtection(row.warnings)}</td>
        
        <td class="px-4 py-4">
          <button type="button" data-employee-id="${htmlInjectionProtection(row.employeeId)}" class="view-employee whitespace-nowrap text-sm font-bold text-[#0046a4] underline hover:text-black focus:outline-none focus:ring-2 focus:ring-[#76b900]">
            View sheet
            <span aria-hidden="true">→</span>
          </button>
        </td>
    </tr>`).join("");

  document.querySelector("#overview-empty").hidden = rows.length !== 0;
  tableStatus.textContent = `${rows.length} of ${(state.overview.overview.rows || []).length} employees shown`;
}

function renderEmployee(employeeId) {
  const employee = state.overview.employees?.[employeeId];
  if (!employee) return;

  state.selectedEmployee = employeeId;
  detailSection.hidden = false;
  detailHeading.textContent = employee.name;
  detailStatus.textContent = `${employee.rows.length} daily ${employee.rows.length === 1 ? "entry" : "entries"} · Existing cells are read-only`;
  openEmployeeSheetLink.href = sheetUrl(employee.sheetId);
  openEmployeeSheetLink.classList.toggle("pointer-events-none", openEmployeeSheetLink.href === "#");

  employeeTableHead.innerHTML =
    `<tr>${["Date", "Shift start", "Pause start", "Pause end", "Shift end", "Pause time", "Shift total time", "Type", "Warnings", "Actions"].map((header) =>
      `<th scope="col" class="border-b border-[#cccccc] px-4 py-4 font-bold">${header}</th>`).join("")}
    </tr>`;
  
  employeeTableBody.innerHTML = employee.rows.map((row, index) => `
    <tr class="border-b border-[#cccccc] last:border-0 hover:bg-[#f7f7f7]">
        <th scope="row" class="px-4 py-4 font-bold">${htmlInjectionProtection(row.date)}</th>
        <td class="px-2 py-4">${htmlInjectionProtection(row.shiftStart)}</td>
        <td class="px-4 py-4">${htmlInjectionProtection(row.pauseStart)}</td>
        <td class="px-4 py-4">${htmlInjectionProtection(row.pauseEnd)}</td>
        <td class="px-4 py-4">${htmlInjectionProtection(row.shiftEnd)}</td>
        <td class="px-4 py-4">${htmlInjectionProtection(row.pauseTime)}</td>
        <td class="px-4 py-4">${htmlInjectionProtection(row.shiftTotalTime)}</td>
        <td class="px-4 py-4">${htmlInjectionProtection(row.type)}</td>
        <td class="px-4 py-4 ${row.warnings !== "—" ? "font-bold text-[#df6500]" : "text-[#757575]"}">${htmlInjectionProtection(row.warnings)}</td>
        
        <td class="px-4 py-4">
          <button type="button" data-row-index="${index}" class="correct-entry whitespace-nowrap text-sm font-bold text-[#0046a4] underline hover:text-black focus:outline-none focus:ring-2 focus:ring-[#76b900]">
            Correct
            <span aria-hidden="true">→</span>
          </button>
        </td>
    </tr>`).join("");
    
  employeeEmpty.hidden = employee.rows.length !== 0;
  detailSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function setLoadedData(data, externalChange = false) {  
  state.overview = data;
  document.querySelector("#period-title").textContent = data.configuration_period || "Configured month";
  openSheetsLink.href = data.spreadsheetUrl || "#";
  openSheetsLink.classList.toggle("pointer-events-none", openSheetsLink.href === "#");
  
  renderOverview();
  
  if (state.selectedEmployee) {
    renderEmployee(state.selectedEmployee);
  }
  syncStatus.textContent = `Loaded from Google Sheets · ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
  
  externalChangeNotice.hidden = !externalChange;
}

async function loadData({ refresh = false } = {}) {
  syncStatus.textContent = "Loading spreadsheet data…";
  document.querySelector("#refresh-preview-button").disabled = true;
  
  try {
    const dataUrl = refresh ? refreshUrl || overviewUrl : overviewUrl || refreshUrl;

    const response = await fetch(dataUrl, {
      headers: {
        Accept: "application/json"
      }
    });
    
    const payload = await response.json();
    
    if (response.ok) {
      console.log(payload);
      setLoadedData(payload.data || payload, Boolean(payload.external_change));
    }
    
    syncStatus.textContent = payload.error;
  } catch (error) {
    tableStatus.textContent = "Unable to load spreadsheet data.";
  } finally {
    document.querySelector("#refresh-preview-button").disabled = false;
  }
}

function openEntryDialog(row = null) {
  const configuration_period = state.overview.configuration_period.split("/");
  const month = configuration_period[0].length === 2 ? `${configuration_period[0]}` : `0${configuration_period[0]}`;
  const year = `${configuration_period[1]}`;
  const days_in_month = getDaysInMonth(Number(month), Number(year));
  
  
  state.editingEntry = row;
  document.querySelector("#entry-dialog-title").textContent = row ? "Correct daily entry" : "Add daily entry";
  entryDate.min = `${year}-${month}-01`;
  entryDate.max = `${year}-${month}-${days_in_month}`;
  entryDate.value = row?.date?.split(".").reverse().join("-") || `${year}-${month}-01`;

  
  entryType.value = row?.type || "Arbeit";
  if (entryType.value === "Arbeit") {
    entryStart.setAttribute("required", true);
    entryEnd.setAttribute("required", true);
  }
  
  entryStart.value = row?.start !== "—" ? row?.start || "" : "";
  entryEnd.value = row?.end !== "—" ? row?.end || "" : "";
  
  entryFormStatus.textContent = "";
  
  if (typeof dialog.showModal === "function") {
    dialog.showModal();
  }
}

async function submitEntry(event) {
  event.preventDefault();
  entryFormStatus.textContent = "Validating entry…";

  const array_decomposed_date = entryDate.value.split("-");
  const year = array_decomposed_date[0];
  const month = array_decomposed_date[1];
  const day = array_decomposed_date[2];

  const normalized_date = `${day}.${month}.${year}`
  const row_index = Number(day) - 1;
  
  const payload = {
    employee_id: state.selectedEmployee,
    date: normalized_date,
    type: entryType.value,
    start: entryStart.value,
    end: entryEnd.value,
    row_index: row_index,
  };

  if (!writeUrl) {
    entryFormStatus.textContent = "Backend write endpoint is not connected yet. The form UI is ready.";
    return;
  }

  try {
    const response = await fetch(writeUrl, {
      method: "POST",
      headers: { 
        "Content-Type": "application/json", 
        "X-CSRFToken": csrfToken()
      },
      body: JSON.stringify(payload),
    });
    
    if (!response.ok) {
      throw new Error("The entry could not be saved.");
    }
    
    dialog.close();
    await loadData();
    
  } catch (error) {
    entryFormStatus.textContent = error.message;
  }
}

document.querySelector("#refresh-preview-button").addEventListener("click", () => loadData({refresh: true}));

employeeSearch.addEventListener("input", () => {
    state.filter = employeeSearch.value.trim();
    renderOverview();
});

overviewTableBody.addEventListener("click", (event) => {
  const button = event.target.closest(".view-employee");
  if (button) {
    renderEmployee(button.dataset.employeeId);
  }
});

employeeTableBody.addEventListener("click", (event) => {
  const button = event.target.closest(".correct-entry");
  if (!button || !state.selectedEmployee) return;
  
  openEntryDialog(state.overview.employees[state.selectedEmployee].rows[Number(button.dataset.rowIndex)]);
});

document.querySelector("#add-entry-button").addEventListener("click", () => openEntryDialog());

document.querySelector("#back-to-overview").addEventListener("click", () => {
  detailSection.hidden = true;
  window.scrollTo(
    {
      top: 0,
      behavior: "smooth"
    });
});

document.querySelector("#close-entry-dialog").addEventListener("click", () => dialog.close());

document.querySelector("#cancel-entry").addEventListener("click", () => dialog.close());

entryForm.addEventListener("submit", submitEntry);

loadData();
