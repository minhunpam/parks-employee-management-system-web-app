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
    - “Download” means fetching the CSV’s contents from Google Drive to the backend using
     its file ID. It does not mean downloading it to the user’s computer or permanently
     saving it on the server.
    - “Parse” means interpreting the downloaded text and converting it into structured data:
  4. Validate every file before changing the spreadsheet.
  5. Identify the employee from the filename and/or CSV content.
  6. Group entries by employee and date.
  7. Calculate the daily result:
      - service start
      - break start
      - break end
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

## CSV Content Parsing
- Check if the parsed filename matches completely with the expected format.
- Decode the CSV content using encoding: `windows-1252`.
- Add all the **date key** into the entry. 
  - Example: June has 30 days, so the date keys will be `01.06.2026`, `02.06.2026`, ..., `30.06.2026`.
  - Reason: I want to maintain a consistent format among the employees. Because if taken from the CSV files, there are days one working, but other doesn't work. So on the day someone doesn't is left blank
- Normalize the data read from the CSV file.
  - Remove blank rows (`[]`), and blank cells (`""`)
  - Remove the first 4 rows adn the last 3 rows which contain unnecessary data
- Check whether the name stored in the CSV file matches the CSV filename

- Read row by row and fetch data values from cell
  - Working date:
    - Check for format matching
    - Check whether the data value's month and year match the expected month and year. Otherwise, the csv file's data is corrupted
  - Working hours:
    - Check format matching
    - If the format matches, append to a list
    - The list must only have 2 elements, which are the start and end times of the working interval
  - Remark:
    - The remark is fetched from the cell value
    - The remark be:
      1. "18=Dienstschluß"
      2. "19=Pause"
      3. `null`

### Handle `entries` dictionary
- Before this handling starts, the `entries` dictionary has form:
```
{
    "<working_date>": [
        {
            "start": "<start_time>",
            "end": "<end_time>",
            "remark": "<remark>"
        },
        {
            "start": "<start_time>",
            "end": "<end_time>",
            "remark": "<remark>"
        },
        ...
    ], 
    ...
}
```

- After the handling, the `entries` dictionary should have the following form:
```
{
    "<working_date>": 
        {
            "shift_start": "<shift_start_time>",
            "pause_start": "<pause_start_time>",
            "pause_end": "<pause_end_time>",
            "shift_end": "<shift_end_time>",
            "shift_total_time": "<shift_total_time>",
            "pause_minutes": "<pause_minutes>",
            "type of day": "<type_of_day>",
            "warnings": "<warnings>",
        },
    "<working_date>": 
        {
            "shift_start": "<shift_start_time>",
            "pause_start": "<pause_start_time>",
            "pause_end": "<pause_end_time>",
            "shift_end": "<shift_end_time>",
            "shift_total_time": "<shift_total_time>",
            "pause_minutes": "<pause_minutes>",
            "type of day": "<type_of_day>",
            "warnings": "<warnings>",
        },
    ...
}
```

- Type of the day includes:
  - "Frei" - off day
  - "Arbeit" - working day

- Calculate the working time
  - Shift gross minutes = End time of the last shift - Start time of the first shift
  - Pause minutes = Sum of all pause gaps
  - Working time = Shift gross minutes - Pause minutes

- Things to consider with the pause gaps 
  - **"ÜBERLAPPUNG" (Overlapping): two CSV intervals occur at the same time**
    - Example:     
      ```text
        08:00–12:00
        11:30–15:00
      ```
     - The second interval starts 30 minutes before the first one ends. Therefore, those 30 minutes overlap.
     - This may indicate:
      - duplicate or incorrect CSV records;
      - manually entered correction data;
      - an employee being assigned to two intervals simultaneously.
     - It is not a pause. The gap calculation is negative:
      ```text
        11:30 - 12:00 = -30 minutes
      ```
  - **LÜCKE (Hole???): employee takes break more than 180 minutes (3 hours)**
  - **Normal case: pause gap is between 5 minutes and 180 minutes**
  - **If employee takes more than 3 breaks during a day, it should give a "P3" warning**

- Pause correction
  - Condition for pause correction is:
    - Employee works more than 360 minutes (6 hours) in a single working day
    - And:
      - Pause minutes < 30 minutes
      - OR The interval between the shift start and the following pause start > 6 hours
  - Recalculate:
    - pause start = shift start + 6 hours 
    - pause end = pause start + 30 minutes
    - shift end = shift start + working time + pause time
  - Warning: `"P6"`