# What Daniel normally does
- Inside `Import` folder, import `.csv` files of the employees with the format: `Schicht_<name_of_the_employee>_<month>_<year>.csv`
- At the end of every month, the folder in emptied automatically thanks to a script
- Run the script: `csv_import.gs` in Apps Script. What we get after the script run is:
  - a list of sheet (within the spreadsheet) of employees. However, those sheets have to be created beforehand
  - maybe `Import` sheet but I will figure it out
    - Daniel says he doesn't use this sheet, so maybe we can omit it
  - There are 2 buttons in a single employee sheet which Daniel (which can be improved through UI):
    - "Safe":
      - Add holidays
    - "Manueller Eintrag":
      - Allows Daniel to manually add the data to the sheet of the target employee
      - Fields:
        - Employee Name
        - Date
        - Working hours
        - Type of shift
        - pause taken
- Run "pause_korrektur.gs" in Apps Script
- Before the monthly summary, he has to manually fix something by comparing/ inspecting his Google Calendar
- Google calendar is shared among employees
- On each day of the month, the chefs have the responsibility to insert the name of each employee to that calendar to signify that that specific employee works on that
- Permission hierarchy in the store:
  - Daniel + Robert: highest permission level (Can add name of employeess + Shift the working hours, in general do everything they want)
  - Chefs: can only name of the employees

## Adding name of the employees on each day
- Name is the most important data
- Time: starting and ending time of the shift don't really matter
- Color: matters as well to differentiate between kitchen and service sector
  - For example:
    - Red: kitchen
    - Grey: service sector

## After manually inserting everything taken from the calendar
- Monthly summaries from sheets
- PDF export that would be sent to every employee without warnings
- Plannungsuebersicht is created and sent to Daniel and Robert
-
