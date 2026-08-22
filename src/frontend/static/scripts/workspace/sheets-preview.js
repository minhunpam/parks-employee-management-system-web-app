import { csrfToken, htmlInjectionProtection } from "../common.js";

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

const mockData = {
    period: "June 2026",
    spreadsheetId: "preview-spreadsheet",
    overview: {
        headers: ["Employee", "Target hours", "Worked hours", "Difference", "Opening balance", "Closing balance", "Vacation balance", "Warnings"],
        rows: [
            { employeeId: "ademir", employee: "Ademir", target: "173.00 h", worked: "168.50 h", difference: "-4.50 h", opening: "-2.00 h", closing: "-6.50 h", vacation: "20.0 d", warnings: "—" },
            { employeeId: "anna", employee: "Anna Berger", target: "173.00 h", worked: "176.00 h", difference: "+3.00 h", opening: "+1.50 h", closing: "+4.50 h", vacation: "18.0 d", warnings: "Review" },
            { employeeId: "milan", employee: "Milan Kovac", target: "160.00 h", worked: "160.00 h", difference: "0.00 h", opening: "0.00 h", closing: "0.00 h", vacation: "22.0 d", warnings: "—" },
        ],
    },
    summary: [
        { label: "Employees", value: "3" },
        { label: "Worked hours", value: "504.50 h" },
        { label: "Vacation days", value: "6.0 d" },
        { label: "Warnings", value: "1" },
    ],
    employees: {
        ademir: { name: "Ademir", sheetId: "ademir-sheet", rows: [
            { date: "01.06.2026", start: "08:00", pause: "30 min", end: "16:30", total: "8.00 h", type: "Arbeit", warning: "—" },
            { date: "02.06.2026", start: "08:00", pause: "30 min", end: "16:30", total: "8.00 h", type: "Arbeit", warning: "—" },
            { date: "03.06.2026", start: "—", pause: "—", end: "—", total: "8.00 h", type: "Urlaub", warning: "—" },
        ] },
        anna: { name: "Anna Berger", sheetId: "anna-sheet", rows: [
            { date: "01.06.2026", start: "09:00", pause: "30 min", end: "17:30", total: "8.00 h", type: "Arbeit", warning: "—" },
            { date: "02.06.2026", start: "09:00", pause: "30 min", end: "17:30", total: "8.00 h", type: "Arbeit", warning: "Missing break" },
        ] },
        milan: { name: "Milan Kovac", sheetId: "milan-sheet", rows: [] },
    },
};

const overviewTableHead = document.querySelector("#overview-table-head");
const overviewTableBody = document.querySelector("#overview-table-body");

const summaryCards = document.querySelector("#summary-cards");
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
const entryFormStatus = document.querySelector("#entry-form-status");

function sheetUrl(sheetId) {
  if (!sheetId || sheetId === "preview-spreadsheet") {
    return "#";
  }

  return `https://docs.google.com/spreadsheets/d/${encodeURIComponent(state.overview.spreadsheetId)}/edit#gid=${encodeURIComponent(sheetId)}`;
}

function renderSummary() {
    summaryCards.innerHTML = (state.overview.summary || []).map((card) => `
        <article class="relative border border-[#cccccc] bg-white p-5">
            <span class="absolute -left-px -top-px h-3 w-3 bg-[#76b900]" aria-hidden="true"></span>
            <p class="text-3xl font-bold">${htmlInjectionProtection(card.value)}</p>
            <p class="mt-2 text-sm text-[#757575]">${htmlInjectionProtection(card.label)}</p>
        </article>
    `).join("");
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
  
  renderSummary();
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
    
    if (!overviewUrl && !refreshUrl) {
        setLoadedData(mockData);
        syncStatus.textContent = "Preview UI is using sample data until the backend endpoint is connected.";
        return;
    }

    const dataUrl = refresh ? refreshUrl || overviewUrl : overviewUrl || refreshUrl;

    const response = await fetch(dataUrl, {
      headers: {
        Accept: "application/json"
      }
    });
    
    const payload = await response.json();
    if (response.ok) {
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
  state.editingEntry = row;
  document.querySelector("#entry-dialog-title").textContent = row ? "Correct daily entry" : "Add daily entry";
  document.querySelector("#entry-date").value = row?.date?.split(".").reverse().join("-") || "";
  document.querySelector("#entry-type").value = row?.type || "Arbeit";
  document.querySelector("#entry-start").value = row?.start !== "—" ? row?.start || "" : "";
  document.querySelector("#entry-end").value = row?.end !== "—" ? row?.end || "" : "";
  document.querySelector("#entry-warning").value = row?.warning !== "—" ? row?.warning || "" : "";
  
  entryFormStatus.textContent = "";
  
  if (typeof dialog.showModal === "function") {
    dialog.showModal();
  }
}

async function submitEntry(event) {
  event.preventDefault();
  entryFormStatus.textContent = "Validating entry…";

  const payload = {
    employee_id: state.selectedEmployee,
    date: document.querySelector("#entry-date").value,
    type: document.querySelector("#entry-type").value,
    start: document.querySelector("#entry-start").value,
    end: document.querySelector("#entry-end").value,
    warning: document.querySelector("#entry-warning").value,
    row_index: state.editingEntry?.rowIndex ?? null,
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
