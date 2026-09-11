# Google Sheets Preview Logic

## Purpose
- The Google Sheets preview provides an in-application abstraction of the configured Google Spreadsheet. It acts as a bridge between PARKS and the real spreadsheet:
  - Managers can view the actual spreadsheet data inside PARKS.
  - Existing spreadsheet data is read-only in the preview.
  - Managers enter or correct data through PARKS UI forms.
  - PARKS writes validated changes back to the actual Google Spreadsheet.
  - Google Sheets remains the source of truth for the spreadsheet workflow.

> The preview is separate from the employee management dashboard. The employee dashboard manages application data stored in `Employee`, `EmployeeMonth`, and `EmployeeYear`. The Sheets preview displays operational data stored in Google Sheets.

## Current spreadsheet structure
- The intended spreadsheet has two types of sheets:
1. **Monthly overview sheet**
   - Represents the configured spreadsheet month.
   - Acts as the landing view for the preview page.

2. **Individual employee sheets**
   - Each sheet belongs to one employee.
   - Contains the employee's daily entries.
   - The current structure has one row for each date.

- The current preview endpoint processes every spreadsheet tab as an employee sheet and matches its title to an application employee. A dedicated overview tab is therefore not supported yet; until that changes, the configured spreadsheet should contain employee tabs that follow the expected naming convention.

For the current version:
```text
employee sheet + date = one unique daily entry
```
> The preview no longer uses `Mitarbeiterdaten` as another preview source. Employee data already populated in the application database remains the responsibility of the employee management features.

## Relationship with application data
The application database and Google Sheets have separate responsibilities:

- `Employee`, `EmployeeMonth`, and `EmployeeYear` support employee management and application-side summaries.
- The Google Spreadsheet contains the monthly operational overview and daily employee entries.

- The Sheets preview should:
  - Use application employee records to identify and label employees where appropriate.
  - Display individual employee sheets for detailed daily data.
  - Use `EmployeeMonth` and `EmployeeYear` only for the rendered summary calculations.
  - Avoid treating application summary records as the source of daily spreadsheet entries.

The existing Employee Dashboard remains the database-backed reporting view. The Sheets preview remains the Google Sheets-backed operational view.

## Preview page structure
### Monthly overview landing page
- The preview opens on the configured spreadsheet period and loads the configured spreadsheet's employee sheets.
- In the current implementation, the monthly overview is an application-rendered summary built from those employee sheets and `EmployeeMonth` records. It is not yet a direct rendering of a dedicated Google Sheets `Monthly overview` tab.
- The page should include:
  - Month and year represented by the spreadsheet.
  - Spreadsheet name.
  - Last synchronized or checked time.
  - A `Refresh data` action.
  - An `Open in Google Sheets` link.
  - A read-only rendering of the monthly employee summary.

- Once a dedicated overview tab is supported, the page should preserve its meaning and structure rather than replacing it with independently calculated application data.

### Employee sheet detail view
- Each employee row or employee reference in the Monthly overview can lead to the corresponding individual employee sheet.

- The detail view should:
  - Render the employee sheet data in the application.
  - Keep existing cells read-only.
  - Display daily entries, including dates, working times, types, and warnings where present.
  - Provide application actions such as `Add entry` and `Correct entry`.
  - Refresh after a successful write.
  - Provide an `Open in Google Sheets` link where useful.

## Current implementation
- `GET /workspace/sheets-preview/` renders the preview shell.
- `GET /workspace/sheets-preview/overview/` validates the Google connection and workspace configuration, reads every sheet, rebuilds the matching `EmployeeMonth`/`EmployeeYear` summaries, and returns JSON containing:
  - the configured period and spreadsheet URL;
  - one summary row per employee sheet;
  - each employee sheet's daily rows and Google `sheetId`.
- Employee sheet names are matched to employees by normalized first name or full name. A missing or ambiguous match aborts the response with an explicit error.
- The frontend supports employee filtering, employee-sheet drill-down, opening the spreadsheet or sheet in Google Sheets, refreshing, and showing warning counts.
- Existing daily cells are displayed as read-only, but the current backend write endpoint does not yet perform a separate stale-data or row-identity check.

## Data-entry behavior
- The preview is not an editable spreadsheet grid. Managers must use PARKS UI forms to enter or correct data.

### Adding an entry
1. The manager selects an employee.
2. The manager opens the employee sheet detail view.
3. The manager selects `Add entry`.
4. PARKS displays a validated data-entry form.
5. PARKS writes the entry to the selected employee sheet through the Google Sheets API.
6. PARKS reloads the preview response, which rebuilds the employee summaries and refreshes the displayed data.
7. The monthly summary is refreshed from the employee sheets.

### Correcting an entry
- The frontend currently identifies the target row by the selected calendar day and sends a zero-based `row_index`; the backend converts it to the corresponding sheet row (`row_index + 2`) and updates columns B:I.
- The current spreadsheet convention therefore assumes one row per calendar day, ordered from the first day of the month. This is an implementation assumption rather than a robust row identity.
- If a future spreadsheet structure permits multiple rows for one date, the entry identity rules will need to be extended.

### Manual entry rules currently implemented
- `Arbeit` requires start and end times in the UI. The backend calculates working minutes from the two times.
- Entries longer than six hours receive an automatically generated pause start/end; the pause duration is currently zero minutes.
- Work on a public holiday is doubled and receives the `Feiertag-Arbeit` warning.
- `Frei` clears warnings and writes zero working hours.
- Other currently selectable types (`Urlaub`, `Krankenstand`, `Feiertag`, and `Extern`) are temporarily treated as eight paid-absence hours by the backend. This rule is provisional and requires business confirmation.
- Every manual write receives the `Manuell` warning unless the `Frei` rule clears warnings.
- The frontend validates that the end time is later than the start time and restricts the date to the configured month.

## Sheet protection
- After import or replacement, the current implementation adds a Google Sheets protected-range request for the whole employee sheet with `warningOnly: true`.
- This currently displays a warning rather than technically preventing direct edits. A strict protection mode still needs to be implemented and verified.
- The intended protection should:
  - Prevent normal direct editing of employee sheet cells in Google Sheets.
  - Allow PARKS to update the protected sheet through its authenticated Google API identity.
  - Include a description such as:

  ```text
  Managed by PARKS. Use the application to add or correct entries.
  ```

> **This protection is a safeguard and a reminder, not an absolute security boundary. The spreadsheet owner can remove or change protection and may be able to edit protected content directly. The application should therefore present PARKS as the intended editing surface while allowing the owner to retain control of the spreadsheet.**

The Monthly overview sheet should also be treated as view-only through PARKS. The application does not provide direct cell editing for any sheet.

## External spreadsheet changes
- Google Sheets does not provide a simple cell-level real-time webhook for this workflow. Real-time synchronization is therefore deferred.
- PARKS should detect changes at these times:
  - When the preview page is opened.
  - When the manager selects `Refresh data`.
  - After PARKS successfully writes data to Google Sheets.

### Snapshot and hash
- PARKS should maintain a last-known snapshot for the relevant spreadsheet data, including:
```text
spreadsheet ID
sheet ID
last known relevant values or value hash
last checked timestamp
```

- When the preview is opened or refreshed:
  1. PARKS fetches the current values from Google Sheets.
  2. PARKS generates a hash from the relevant values.
  3. PARKS compares the new hash with the stored hash.
  4. If the hash differs, PARKS reloads the latest values and informs the manager that the spreadsheet was changed outside PARKS.
  5. PARKS stores the new snapshot and timestamp.

- The change check applies to both:
  - The Monthly overview sheet.
  - Individual employee sheets.

- Snapshot/hash comparison is planned but is not implemented in the current preview endpoint. The current `Refresh data` action simply fetches the latest spreadsheet values.
- Initial synchronization is therefore explicit and predictable rather than real-time. Automatic polling or Apps Script-based synchronization can be considered later if required.

## Employee and sheet matching
- The long-term preferred mapping is a stable application employee identifier to a Google Sheets `sheetId`. Names can change and may not be unique.
- For the current version, CSV filenames and spreadsheet structure only provide employee names. Therefore, employee names are used as the temporary matching key.

Name matching must:
- Normalize case and whitespace.
- Handle expected formatting differences consistently.
- Require an exact match after normalization.
- Detect duplicate employee names before importing or linking data.
- Stop with an explicit error when a name matches multiple employees.
- Never assign data arbitrarily when a name is ambiguous.

- The current rule is:

> A CSV file or employee sheet is valid only when its normalized employee name matches exactly one active employee.

The matching logic should remain isolated so that a future stable employee ID can replace name matching in CSV filenames, CSV content, sheet metadata, and preview links.

## Monthly overview and employee sheet consistency

- PARKS must treat Google Sheets as authoritative for daily employee data:
  - Employee details are read from the actual employee sheets.
  - The current monthly summary is assembled by PARKS from those rows and refreshed `EmployeeMonth` records.
  - A dedicated Google Sheets Monthly overview tab is a planned follow-up, not part of the current endpoint.

- After PARKS changes an employee sheet, it must refresh the employee view and the Monthly overview because the overview may contain formulas or generated values that depend on the employee sheet.

## Errors and safeguards
- The preview should clearly report when:
  - The configured spreadsheet cannot be accessed.
  - The Monthly overview sheet is missing.
  - An expected employee sheet is missing.
  - An employee name matches multiple records.
  - A protected sheet cannot be updated by PARKS.
  - Google Sheets values changed while the manager was working with stale preview data.

> PARKS should not silently display or update data for the wrong employee.

## Deferred functionality

The following are outside the initial preview implementation:

- Real-time cell synchronization.
- Automatic background polling.
- Direct editing of spreadsheet cells in the preview.
- Removing or overriding Google Sheets protection through PARKS.
- Stable employee IDs embedded in CSV files or sheet metadata.
- Support for multiple rows for the same employee and date.
- Supporting a dedicated Google Sheets Monthly overview tab instead of the current application-rendered summary.
