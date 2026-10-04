# Proposal

## Why

The employee detail table displays daily entries as one continuous list, making it harder for managers to scan a month and distinguish one calendar week from the next. Adding explicit weekly separators will improve readability without changing the underlying spreadsheet data.

## What Changes

- Add a presentation-only row after each calendar week in the employee detail table, labeled “End of week <n>”.
- Number weeks within the displayed month using calendar weeks that begin Monday and end Sunday; partial weeks at either end of the month count.
- Keep daily entries, correction actions, and spreadsheet data unchanged.

## Capabilities

### New Capabilities
- `employee-sheet-preview`: Covers rendering employee daily entries in the Sheets preview, including calendar-week grouping cues.

### Modified Capabilities

## Impact

- Frontend rendering in `src/frontend/static/scripts/workspace/sheets-preview.js`.
- Automated frontend tests for employee-table week boundaries and separator placement. No API, spreadsheet, or database changes are expected.
