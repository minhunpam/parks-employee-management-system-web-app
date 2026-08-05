# Main logic frontend & backend
- Once workspace configuration is complete, the user is navigated to this page.
- The page will display the created configuration:
  - Drive root folder ID
  - Spreadsheet ID

## CSV Importing
- There is a button called "Import CSV" which on click event, will it will make a request to the the `workspace:import_csv` endpoint to trigger the csv import process.
- We don't need to send the folder and spreadsheet IDs from the frontend because the backend already knows them from the logged-in user's session.

### `csv_import()`
- Validation before the CSV importing logic:
  - Validate connection and configuration
  - Validate folder and spreadsheet IDs
    - The previous configuration might become stale, since the user can delete either of them
- After that, the returned folder and spreadsheet would be handled

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

