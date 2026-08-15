# Employee Dashboard

## Purpose
- The Employee Dashboard is the manager-facing interface for reviewing employee records and their monthly and yearly summaries.
- The dashboard manages data stored in the Django database:
  - `Employee` — employee master data
  - `EmployeeMonth` — monthly working-hour and vacation summaries
  - `EmployeeYear` — yearly vacation summaries
  
> Google Sheets remains relevant to daily shift details and CSV import, but the spreadsheet preview and manual-entry workflow are intentionally deferred. They are not part of this dashboard design yet.

## Page structure
```text
Employee Dashboard
├── Employees
│   ├── Summary cards
│   ├── Filters and search
│   └── Paginated employee table
├── Monthly summaries
│   ├── Summary cards
│   ├── Filters and search
│   └── Paginated monthly table
└── Yearly summaries
    ├── Summary cards
    ├── Filters and search
    └── Paginated yearly table
```
- The dashboard uses three horizontal tabs:
```text
Employees | Monthly summaries | Yearly summaries
```
> The **Employees** tab is active by default.

## Header
- Use the existing project design system:
  - black hero/header surface
  - white heading text
  - NVIDIA Green (`#76b900`) eyebrow and primary action
  - angular layout with no shadows
  - maximum content width of approximately 1280px
- Header content:

```text
Employee records
Employee management.
Review employee records, monthly working balances, and yearly vacation summaries.

[Register employee]
```
> The **Register employee** button is visible only on the Employees tab. It links to the employee registration page.

## Tab navigation
- The tabs appear below the header on the light page canvas.
  - Use horizontal segmented tabs.
  - Active tab uses a black bottom border and black text.
  - Inactive tabs use a transparent bottom border and muted gray text.
  - Tabs must expose `aria-selected` state.
  - On mobile, tabs remain horizontally scrollable rather than collapsing into a select input.

- Changing tabs must:
  1. update the active tab state;
  2. update the visible filters;
  3. reset pagination to page 1;
  4. fetch and display the selected table data.

## Summary cards
- Each tab has a summary strip above its filters and table.
- Cards use the design system's `callout-stat` style:
  - white background
  - 1px hairline border (`#cccccc`)
  - green 12px corner square
  - large black number
  - small muted label
  - no shadow

> Summary values react to the active filters. When filters are active, the cards summarize the filtered result set rather than the entire database.

### Employees cards
```text
Total employees | Active employees | Archived employees
```

### Monthly summaries cards
```text
Employees with records | Total closing hour balance | Total vacation days used
```

### Yearly summaries cards
```text
Employees with records | Total vacation entitlement | Total remaining balance
```

## Filters
- Filters apply automatically. There is no separate Apply button.
- Changing a filter must:
  1. reset pagination to page 1;
  2. request the filtered table data;
  3. update the summary cards;
  4. update the empty state and pagination information.

- The filter toolbar uses a light gray background (`#f7f7f7`) and a hairline border.

### Employees filters
- Search by first name, last name, or email
- Working status:
  - All statuses
  - Active
  - Archived

### Monthly summaries filters
- Search by employee name or email
- Year
- Month

### Yearly summaries filters
- Search by employee name or email
- Year

- A **Reset filters** action returns all visible filters to their defaults and reloads the unfiltered table.
> The reset refresh must happen after the browser has applied the form's default values. Otherwise, the refresh can read the old values during the `reset` event.

## Employees table
- The columns follow `EmployeeAdmin` in `src/backend/employees/admin.py`:
```text
First name | Last name | Email |Working status|Employment start date | Employment end date
```
- The Employees table is sortable by the relevant columns and is paginated with 25 rows per page by default.

## Monthly summaries table
- The columns follow `EmployeeMonthAdmin` in `src/backend/employees/admin.py`:
```text
Employee | Year | Month | Opening hour balance | Closing hour balance |Opening vacation balance |Closing vacation balance
```
- The table is globally scoped, so managers can compare employees. It supports employee search, year filtering, month filtering, sorting, and pagination.

## Yearly summaries table
- The columns follow `EmployeeYearAdmin` in `src/backend/employees/admin.py`:
```text
Employee | Year | Annual vacation days | Carried-over vacation days | Vacation balance
```

- The table is globally scoped and supports employee search, year filtering, sorting, and pagination.

## Table behavior
- All three tables:
  - are globally scoped rather than limited to one selected employee;
  - support pagination;
  - show 25 rows per page by default;
  - support sorting through sortable table headers;
  - retain all defined columns on small screens through horizontal scrolling;
  - display a loading status while data is requested;
  - use accessible table headers and live status text.

- Pagination displays the current range and total number of records:
```text
1–25 of 128

[Previous] [Next]
```

- The Previous and Next buttons are disabled when the user is at the first or last page.

## Empty states
- The empty state must distinguish between an empty database and filters that return no results.

### Employees with no records
```text
No employees registered yet
Register an employee to begin managing records.

[Register employee]
```

### Filtered tables with no matching records
```text
No records match these filters
Reset the filters to see all available records.

[Reset filters]
```

## Responsive behavior
### Desktop
- Header content uses a two-column layout with the primary action aligned to the right.
- Summary cards appear in a three-column row.
- Filter controls use a horizontal grid.
- Tables use the full content width.

### Mobile
- Header content stacks vertically.
- The Register employee action remains full-width or naturally sized for touch use.
- Tabs become horizontally scrollable.
- Filters stack vertically.
- Summary cards stack into one column.
- Tables use horizontal scrolling rather than hiding columns.
- All interactive controls maintain at least a 44px touch target.

## Data endpoint
- The dashboard page loads table data through:

```text
/employees/employee-dashboard/data/
```

The endpoint accepts the current dashboard state, including:
- `tab`
- `page`
- `page_size`
- `search`
- `status`
- `year`
- `month`
- `sort`
- `direction`

It returns:
- the selected tab;
- table rows;
- total record count;
- current page and page size;
- summary-card values.

> The frontend escapes dynamic values before inserting them into HTML. This prevents employee-provided or database-provided values from being interpreted as markup a.k.a HTML injection.

## Deferred functionality

The following are intentionally outside the current Employee Dashboard design:

- Google Sheets preview page
- Daily employee shift detail view
- Add manual entry button
- Manual entry dialog
- Recalculation of `EmployeeMonth` and `EmployeeYear` after manual entries
- Employee row detail page or drawer

Those features should be designed separately once the dashboard's global summary views are complete.
