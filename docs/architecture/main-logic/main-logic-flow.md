# Main logic frontend & backend
- Once workspace configuration is complete, the user is navigated to this page.
- The page will display the created configuration:
  - Drive root folder ID
  - Spreadsheet ID

## CSV Importing
- The workspace entry page has separate `Check for CSV files` and `Import files` actions.
- The check action calls `workspace:csv-import-check`; the import action calls `workspace:csv-import`.
- Neither request sends folder or spreadsheet IDs because the backend reads them from the logged-in user's workspace configuration.

### `csv_import()`
- Validation before the CSV importing logic:
  - Validate connection and configuration
  - Validate folder and spreadsheet IDs
    - The previous configuration might become stale, since the user can delete either of them
- After that, the returned folder and spreadsheet would be handled
- From the returned folder, the month/year subfolders are recursively created if they don't exist via `prepare_csv_import_folder()` which eventually returns an import state
- Depending on `import_state`, the endpoints return:
  - `awaiting_upload` when the previous-month folder is empty;
  - `invalid_files` when filenames do not follow the required convention;
  - `ready` with the files and spreadsheet metadata when files are valid.
- The import endpoint revalidates the folder before parsing each CSV, checks the expected month/year and employee data, creates employee sheets and headers when needed, replaces the affected employee rows, and updates application summaries.
- Successfully imported Drive files are archived. A spreadsheet update or archive failure is reported separately so the manager knows whether the spreadsheet was changed.

---

### Folder handling:
- Folder hierarchy:
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

#### Explain the regular expression pattern used to validate CSV filenames
```python
CSV_FILENAME = re.compile(
    r"^Schicht_(?P<employee_name>.+)_(?P<month>[^_]+)_(?P<year>20\d{2})\.csv$"
)
```
- `r"..."` - raw string. Backslashes are treated as literal characters
- `^` - beginning of the string
- `Schicht_` - literal string `Schicht_`

- `(?P<employee_name>.+)`
  - `(` - start a capturing group
  - `?P<employee_name>` - named group `employee_name`
  - `.+` - matches any non-empty string
  - `)` - end the capturing group

- `_` - after the employee name, matches the underscore separator between the employee name and the month

- `(?P<month>[^_]+)` - named group `month`
  -  `[^_]+` - matches one or more characters that are not underscores
    - `[..]` defines a character class
    - `^` inside the character class
    - `_` is the excluded character
    - `+` - matches one or more characters

- `_(?P<year>20\d{2})` - named group `year`
  - `20\d{2}` - matches any string starting with `20` and followed by two digits === 2000 - 2099

- `\.csv`
  - `\.` - literal `.` character. The dot must be escaped with a backslash because an unescaped dot means "any character"
  - `csv` - literal `csv` string
- `$` - end of the string

## Google Sheets preview
- The workspace entry page links to the Sheets preview after a workspace has been configured.
- `sheets_preview_overview()` validates the user's Google connection and configured Drive/spreadsheet resources before reading the spreadsheet.
- For each spreadsheet tab, the backend reads employee rows from columns A:I, matches the tab name to an employee, rebuilds the employee's monthly and yearly summary records, and returns the daily rows plus the summary data as JSON.
- The frontend renders the employee overview, supports name filtering and employee-sheet drill-down, and can open the spreadsheet or individual sheet in Google Sheets.
> The preview is read-only except for the application entry form. It does not yet render a dedicated Google Sheets Monthly overview tab or perform snapshot/hash-based external-change detection.

## Manual spreadsheet entries
- The employee detail view sends a date, entry type, start/end times, selected employee sheet, and row index to the Sheets write endpoint.
- The backend writes columns B:I of the calculated sheet row and then the frontend reloads the preview, rebuilding the database summaries from Google Sheets.
- Current rules are:
  - `Arbeit`: calculate working time from start/end; work longer than six hours gets an automatically generated zero-minute pause.
  - Public-holiday work is doubled and marked `Feiertag-Arbeit`.
  - `Frei`: reset the row to zero hours and clear warnings.
  - Other selectable absence types currently become eight paid-absence hours; this is provisional business logic.
  - Manual writes are marked with `Manuell` unless the row is reset with `Frei`.
- The UI requires start/end only for `Arbeit`, checks that end is later than start, and limits dates to the configured month.
