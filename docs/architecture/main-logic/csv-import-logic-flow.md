# CSV Import Logic Flow

## Introduction
- After the user uploads all employee CSV files to the matching previous-month folder, the user can check the folder and then explicitly start importing the data into the configured Google Sheet spreadsheet.
- The CSV import consists of two separate user actions:
  1. **Check CSV files** — inspect the previous-month folder and report whether it is ready.
  2. **Import data** — only available after valid CSV files have been found; parse the files and update the spreadsheet.

- The frontend should display a separate **Import data** button next to the successful check result. The first action must not modify spreadsheet data.

## Folder and filename rules
- The backend uses the configured Drive root folder and creates the following structure when necessary:

```text
root_folder/
└── Import/
    └── {zero-padded previous month}_{year}/
        └── Schicht_{employee_name}_{German month}_{year}.csv
```

For example:

```text
Import/06_2026/Schicht_Ademir_Juni_2026.csv
```

Only active CSV files in the target month folder are considered. Files containing the archive suffix are ignored:

```text
Schicht_Ademir_Juni_2026[ARCHIVED].csv
```

Active filenames must follow the existing convention and must match the target month and year. Invalid filenames prevent the import from proceeding and are returned to the user.

## Check phase

The check endpoint should:

1. Validate the logged-in user’s Google connection and workspace configuration.
2. Validate that the configured root folder and spreadsheet still exist and are editable.
3. Create `Import` if it does not exist.
4. Create the previous-month folder if it does not exist.
5. Ignore archived files. 
6. Validate the remaining CSV filenames.
7. Return one of these states:
   - `awaiting_upload` — no active CSV files exist.
   - `invalid_files` — one or more active files have invalid names.
   - `ready` — valid active CSV files exist.

When the result is `ready`, the frontend shows the **Import data** button and the number of files found. The check action itself does not parse or write CSV data to the spreadsheet.

## Import phase

The import endpoint is called only after the user clicks **Import data**.

- The import must follow this order:
  1. Revalidate the Google connection, workspace configuration, folder, and spreadsheet.
  2. Reinspect the target month folder and ignore `[ARCHIVED]` files.
  3. Download and parse every active CSV file.
  4. Validate every file before changing the spreadsheet.
  5. Identify the employee from the filename and/or CSV content.
  6. Group entries by employee and date.
  7. Calculate the daily result:
      - service start
      - break start and end
      - service end
      - break minutes
      - working hours
      - type
      - warnings
  8. If all files are valid, update the spreadsheet in one batch where possible.
  9. After the spreadsheet update succeeds, rename each successfully imported file by adding `[ARCHIVED]` before `.csv`.
  10. Return an import summary to the frontend.

- The `IMPORT` sheet is intentionally not written. The separate archive folder is also not used because the `Import` folder is already divided into month subfolders.

## Spreadsheet model and replacement behavior

- Each configured spreadsheet represents one month. Employee sheets must not be cleared entirely before importing. Existing content and formatting should be preserved.

- The import is repeatable by replacing data at the employee-and-date level:
  1. Identify the employee from the CSV filename/content.
  2. Determine all dates represented by that CSV.
  3. Remove existing generated rows for that employee on those dates.
  4. Insert the newly parsed rows for those dates.

- The replacement unit is the complete `employee + date`, not an individual spreadsheet row. A single day can generate multiple rows because multiple breaks may be represented separately.
- For example, when a corrected file contains data for `Ademir + 04.06.2026`, all existing generated rows for Ademir on June 4 are replaced by the newly calculated rows. Data for other employees and dates remains unchanged.
- This also makes retries safe. If the spreadsheet update succeeds but file renaming fails, the file remains active and may be processed again. Reprocessing replaces the same employee/date rows instead of appending duplicates.

## Failure behavior
- CSV parsing and validation are performed for all active files before spreadsheet changes are made. If any file fails validation, the import must:
  - write nothing to the spreadsheet;
  - rename nothing in Drive; and
  - report the affected filename and reason to the user.

- Spreadsheet updates and Drive renames are separate Google API operations and cannot form one atomic transaction. Therefore, if the spreadsheet update succeeds but a rename fails, the import should report the archive failure while preserving the written data. A later retry remains safe because of the employee-and-date replacement behavior.

## Existing transformation logic

The old Apps Script in `src/frontend/apps_scripts/csv_imports.js` is a reference for the transformation rules. It currently:

- reads CSV files;
- extracts dates and working intervals;
- groups entries by employee and day;
- detects breaks and overlaps;
- calculates break duration and working hours;
- creates warning values; and
- writes employee sheets.

The backend implementation should adapt these rules to the current architecture and previous-month subfolder structure. It should not retain the old behavior of clearing columns `A:I`, writing the `IMPORT` sheet, or moving files to a separate archive folder.

## Sample CSV

A sample input file is available in `csv_raw_data/`, for example:

```text
csv_raw_data/Schicht_Ademir_Juni_2026.csv
```
