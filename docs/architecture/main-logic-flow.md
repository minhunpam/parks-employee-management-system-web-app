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
          |--This folder follows naming convention `{month}_{year}`
              |-- CSV files of each employee, follow naming convention: `Schicht_{employee_name}_{month}_{year}.csv`
```
- It will start searching in the root folder
- If there is no `Import` folder, create that folder and recursively create the month/year subfolders
- If there is `Import` folder, but it is empty with no subfolders, recursively create the month/year subfolders
- If there is `Import` folder, and it already contains subfolders, look inside the subfolder of interest
  - For example, currently it is August, which means we need to work with previous month, which is July. If the July subfolder is empty, ask the user to upload employee csv files into that subfolder
  - If the July subfolder is not empty, iteratively check the naming convention of the CSV files inside it



