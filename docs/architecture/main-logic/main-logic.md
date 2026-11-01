# Main logic frontend & backend

Once workspace configuration is complete, the user is navigated to this page. The page will display the created configuration: Drive root folder ID, Spreadsheet ID

The workspace entry page has separate `Check for CSV files` and `Import files` actions:
  1. The check action calls `workspace:csv-import-check`
  2. The import action calls `workspace:csv-import`

> **Neither request sends folder or spreadsheet IDs because the backend reads them from the logged-in user's workspace configuration.**

## CSV Importing

Import contect validation before the CSV importing logic:
1. Validate connection and configuration
2. Validate folder and spreadsheet IDs
  - **WHY**:  The previous configuration might become stale, since the user can delete either of them
3. Prepare the CSV import folder
  - **HOW**: `<month><year>` subfolders are recursively created if they don't exist

The validate import context would give an import state with which we can determine what actions users need to do afterwards. There are 3 kinds of statuses:
  1. `awaiting_upload` when the previous-month folder is empty ---> Users need to upload the CSV files to the configured folder
  2. `invalid_files` when filenames do not follow the required convention ---> Rename/Fix the file(s)
  3. `ready` with the files and spreadsheet metadata when files are valid ---> Ready for CSV importing

The import endpoint revalidates the folder before parsing each CSV, checks the expected month/year and employee data, creates employee sheets and headers when needed, replaces the affected employee rows, and updates application summaries.
- Successfully imported Drive files are archived. A spreadsheet update or archive failure is reported separately so the manager knows whether the spreadsheet was changed.

---

### Folder handling

Folder hierarchy:
```
root_folder
    |--Import
          |--8_2026
          |--9_2026
          |--10_2026
          ...
          |--This folder follows naming convention `{zero-padded month}_{year}`. Example: `08_2026`
              |-- CSV files of each employee, follow naming convention: `Schicht_{employee_name}_{month in german}_{year}.csv`. Example: `Schicht_Ademir_Juni_2026.csv`
```
- It will start searching in the root folder
- If there is no `Import` folder, create that folder and recursively create the month/year subfolders
- If there is `Import` folder, but it is empty with no subfolders, recursively create the month/year subfolders
- If there is `Import` folder, and it already contains subfolders, look inside the subfolder of interest
  - For example, currently it is August, which means we need to work with previous month, which is July. If the July subfolder is empty, ask the user to upload employee csv files into that subfolder
  - If the July subfolder is not empty, iteratively check the naming convention of the CSV files inside it

## Google Sheets preview

The workspace entry page links to the Sheets preview after a workspace has been configured. For each spreadsheet tab, the backend reads employee rows from columns A:I, matches the tab name to an employee, rebuilds the employee's monthly and yearly summary records, and returns the daily rows plus the summary data as JSON.

The frontend renders the employee overview, supports name filtering and employee-sheet drill-down, and can open the spreadsheet or individual sheet in Google Sheets.

> **The preview is read-only and users can only modify the sheet via manual entry**

## Manual spreadsheet entries
- The employee detail view sends a date, entry type, start/end times, selected employee sheet, and row index to the Sheets write endpoint.
- The backend writes columns B:I of the calculated sheet row and then the frontend reloads the preview, rebuilding the database summaries from Google Sheets.
- Current rules are:
  - `Arbeit`: calculate working time from start/end; work longer than six hours gets an automatically generated zero-minute pause.
  - Public-holiday work is doubled and marked `Feiertag-Arbeit`.
  - `Frei`: reset the row to zero hours and clear warnings.
  - Other selectable absence types (`Urlaub`, `Krankenstand`, `Feiertag`, and `Extern`) receive paid-absence hours calculated as `weekly_target_hours / work_days_per_week`, rounded to two decimals.
  - Manual writes are marked with `Manuell` unless the row is reset with `Frei`.
- The UI requires start/end only for `Arbeit`, checks that end is later than start, and limits dates to the configured month.
