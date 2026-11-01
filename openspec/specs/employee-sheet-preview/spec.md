# employee-sheet-preview Specification

## Purpose

The employee sheet preview presents monthly daily entries in a way that lets managers scan the calendar period and distinguish its weeks. It provides visual grouping without altering spreadsheet data.

## Requirements

### Requirement: Employee entries are separated by calendar week
The employee detail table SHALL display an “End of week <n>” separator after each calendar week represented in the displayed month. Calendar weeks begin on Monday and end on Sunday; partial weeks at month boundaries count as weeks. Week numbering restarts at 1 for each month.

#### Scenario: Week ends within the month
- **WHEN** an employee table contains entries through a Sunday and the next entry is in the following calendar week
- **THEN** a separator labeled with the ending week's number is displayed after that Sunday's entry

#### Scenario: Month begins mid-week
- **WHEN** the first day of the displayed month falls after Monday
- **THEN** the days from the first through that week's Sunday belong to week 1

#### Scenario: Month ends before Sunday
- **WHEN** the displayed month ends before the calendar week's Sunday
- **THEN** a separator for the final partial week is displayed after the month's final entry

#### Scenario: Week number changes across a month boundary
- **WHEN** the displayed employee entries belong to one configured month
- **THEN** week numbering is based on calendar weeks within that month and starts at 1, regardless of ISO week numbers

#### Scenario: Separator does not represent an employee entry
- **WHEN** a manager views the employee detail table containing week separators
- **THEN** separators do not replace or alter daily entries and do not offer entry-correction actions
