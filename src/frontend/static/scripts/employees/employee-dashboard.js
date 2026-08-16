const page = document.querySelector("#employee-dashboard");
const apiUrl = page.dataset.apiUrl;
const employeeDetailsUrl = page.dataset.employeeDetailsUrl;

const state = {
  tab: "employees",
  page: 1,
  pageSize: 25,
  sort: "default",
  direction: "asc"
};

const htmlInjectionProtection = (value) =>
  String(value ?? "").replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    '"': "&quot;"
  }[char])
);

const searchField = document.querySelector("#search");

const statusDropDown = document.querySelector("#status-drop-down");
const yearDropDown = document.querySelector("#year-drop-down");
const monthDropDown = document.querySelector("#month-drop-down");
const summaryCardsContainer = document.querySelector("#summary-cards");

const tableHead = document.querySelector("#table-head");
const tableBody = document.querySelector("#table-body ");
const tableStatus = document.querySelector("#table-status");

const tableDefinitions = {
  employees: {
    headers: ["ID", "First name", "Last name", "Email", "Working status", "Employment start", "Employment end"],
    fields: ["id", "first_name", "last_name", "email", "working_status", "employment_start_date", "employment_end_date"],
    sortable: [null, "first_name", "last_name", "email", "working_status", "employment_start_date", null],
    cards: [
      ["total", "Total employees"],
      ["active", "Active employees"],
      ["archived", "Archived employees"],
    ],
  },
  monthly: {
    headers: ["Employee", "Year", "Month", "Opening hour balance", "Closing hour balance", "Opening vacation balance", "Closing vacation balance"],
    fields: ["employee", "year", "month", "opening_hour_account_balance", "closing_hour_account_balance", "opening_vacation_balance", "closing_vacation_balance"],
    sortable: ["employee", "year", "month", "opening_hour_account_balance", "closing_hour_account_balance", "opening_vacation_balance", "closing_vacation_balance"],
    cards: [
      ["records", "Employees with records"],
      ["closing_hours", "Total closing hour balance"],
      ["vacation_used", "Total vacation days used"]
    ],
  },
  yearly: {
    headers: ["Employee", "Year", "Annual vacation days", "Carried-over vacation days", "Vacation balance"],
    fields: ["employee", "year", "annual_allowed_vacation_days", "carried_over_vacation_days", "vacation_balance"],
    sortable: ["employee", "year", "annual_allowed_vacation_days", "carried_over_vacation_days", "vacation_balance"],
    cards: [
      ["records", "Employees with records"],
      ["entitlement", "Total vacation entitlement"],
      ["balance", "Total remaining balance"]
    ],
  },
};

function loadYears() {
  const current_year = new Date().getFullYear();
  
  for (let value = current_year; value >= current_year - 5; --value) {
    yearDropDown.insertAdjacentHTML(
      "beforeend",
      `<option value="${value}">${value}</option>`);
  }
  
  for (let value = 1; value <= 12; ++value) {
    monthDropDown.insertAdjacentHTML(
      "beforeend",
      `<option value="${value}">${String(value).padStart(2, "0")}</option>`);
  }
}


function updateFilters() {
  document.querySelector("#status-filter").hidden = state.tab !== "employees";
  document.querySelector("#year-filter").hidden = state.tab === "employees";
  document.querySelector("#month-filter").hidden = state.tab !== "monthly";
  document.querySelector("#register-link").hidden = state.tab !== "employees";
}

function renderSummaryCards(summary) {
  summaryCardsContainer.innerHTML = tableDefinitions[state.tab].cards
    .map(
      ([key, label]) => `
        <article class="relative border border-[#cccccc] bg-white p-6">
          <span
            class="absolute -left-px -top-px h-3 w-3 bg-[#76b900]"
            aria-hidden="true">
          </span>

          <p class="pt-2 text-3xl font-bold">${htmlInjectionProtection(summary[key])}</p>
          
          <p class="mt-2 text-sm text-[#757575]">${label}</p>
        </article>
      `
    ).join("");
}

function renderTable(data) {
  const definition = tableDefinitions[state.tab];
  
  const isEmployeesTab = state.tab === "employees";
  const hasEmployeeFilters = searchField.value || statusDropDown.value;
  const hasRows = data.rows.length > 0;

  const renderHeader = (header, index) => {
    const sortField = definition.sortable[index];

    if (!sortField) {
      return `
        <th scope="col" class="border-b border-[#cccccc] px-5 py-4 font-bold">
          ${header}
        </th>
      `;
    }

    return `
      <th scope="col" class="border-b border-[#cccccc] px-5 py-4 font-bold">
        <button type="button" class="sort-button text-left hover:text-black" data-sort="${sortField}">
          ${header}
          <span aria-hidden="true">↕</span>
        </button>
      </th>
    `;
  };

  tableHead.innerHTML = `
    <tr>
      ${definition.headers.map(renderHeader).join("")}
    </tr>
  `;
  
  const renderCell = (row, field) => {
    if (isEmployeesTab && field === "first_name") { 
      const employeeId = row.id;
      
      return `
        <td class="px-5 py-4">
          <a
            class="text-sm text-[#0046a4] underline"
            href="${employeeDetailsUrl.replace('/0', `/${employeeId}`)}">
            ${htmlInjectionProtection(row[field])}
          </a>
        </td>`;
    }
    
    return `<td class="px-5 py-4">${htmlInjectionProtection(row[field])}</td>`;
  };

  const renderRow = (row) => `
    <tr class="border-b border-[#cccccc] last:border-0 hover:bg-[#f7f7f7]">
      ${definition.fields.map((field) => renderCell(row, field)).join("")}
    </tr>
  `;

  tableBody.innerHTML = data.rows.map(renderRow).join("");

  document.querySelector("#empty-state").classList.toggle("hidden", hasRows);
  document.querySelector("#empty-title").textContent = isEmployeesTab && !hasEmployeeFilters
      ? "No employees registered yet"
      : "No records match these filters";
  document.querySelector("#empty-message").textContent =
    isEmployeesTab && !hasEmployeeFilters
      ? "Register an employee to begin managing records."
      : "Reset the filters to see all available records.";

  tableStatus.textContent = hasRows
    ? `Showing ${data.rows.length} of ${data.total} records`
    : "";

  const firstRow = data.total
    ? (data.page - 1) * data.page_size + 1
    : 0;
  const lastRow = Math.min(data.page * data.page_size, data.total);

  document.querySelector("#page-summary").textContent = data.total
    ? `${firstRow}–${lastRow} of ${data.total}`
    : "No records";
  document.querySelector("#previous-page").disabled = data.page <= 1;
  document.querySelector("#next-page").disabled = data.page * data.page_size >= data.total;
}

async function loadData() {
  const params = new URLSearchParams(
    {
      tab: state.tab,
      page: state.page,
      page_size: state.pageSize,
      search: searchField.value,
      status: statusDropDown.value,
      year: yearDropDown.value,
      month: monthDropDown.value,
      sort: state.sort,
      direction: state.direction
    }
  );
  
  tableStatus.textContent = "Loading records…";
  try {
    const response = await fetch(`${apiUrl}?${params}`);
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.error || "Unable to load records.");
    }
    
    renderSummaryCards(data.summary);
    renderTable(data);
  } catch (error) {
      tableStatus.textContent = error.message;
      tableBody.innerHTML = "";
  }
}

function refresh() {
  state.page = 1;
  loadData();
}

loadYears();
updateFilters();
loadData();

document.querySelectorAll(".dashboard-tab").forEach((button) => button.addEventListener("click", () => {
  state.tab = button.dataset.tab;
  document.querySelectorAll(".dashboard-tab").forEach((tab) => {
      const active = tab === button;
      tab.classList.toggle("text-[#757575]", !active);
      tab.setAttribute("aria-selected", active);
  });

  updateFilters();
  refresh();
}));


["search", "status-drop-down", "year-drop-down", "month-drop-down"].forEach((id)=> document.querySelector("#" + id).addEventListener(id === "search" ? "input" : "change", refresh));

document.querySelector("#filters").addEventListener("reset", () => setTimeout(refresh));

document.querySelector("#previous-page").addEventListener("click", () => {
  state.page -= 1;
  loadData();
});

document.querySelector("#next-page").addEventListener("click", () => {
  state.page += 1;
  loadData();
});

tableHead.addEventListener("click", (event) => {
  const button = event.target.closest(".sort-button");
  if (!button) return;
  
  if (state.sort === button.dataset.sort) {
    state.direction = state.direction === "asc" ? "desc" : "asc";
  }
  else {
    state.sort = button.dataset.sort; state.direction = "asc";
  }

  state.page = 1;
  loadData();
});