# Integration of weekly target hours for employees

## Purpose

Make `weekly_target_hours` the canonical working-agreement input while retaining `monthly_target_hours` as a stored derived value for existing summaries and integrations.

## Employee fields

- `work_days_per_week` remains an integer from `1` to `7`, defaulting to `5`.
- `weekly_target_hours` is a decimal from `20.00` to `40.00`, inclusive, defaulting to `40.00`.
- `monthly_target_hours` remains stored with two decimal places and is calculated by the server.

The monthly conversion is:

```text
monthly_target_hours = weekly_target_hours * 13 / 3
```

Calculations use `Decimal` and round to two decimal places with `ROUND_HALF_UP`.

## Migration strategy

Implement this as a Django schema migration followed by a reversible `RunPython` data migration.

For existing employees, calculate the new weekly value from the existing monthly value:

```text
weekly_target_hours = existing_monthly_target_hours * 3 / 13
```

Round the new weekly value to two decimal places, but preserve the existing monthly value. For example:

```text
173.00 monthly hours -> 39.92 weekly hours
```

New employees must provide only `weekly_target_hours`. The backend calculates and stores `monthly_target_hours`; clients must not independently control both values.

## Updating monthly summaries

When an employee's weekly target changes:

- Update the calendar month containing today automatically.
- Recalculate that month's `target_working_hours`, `hour_difference`, and `closing_hour_account_balance`.
- Propagate the new closing hour-account balance as the opening balance of later months.
- Do not update unrelated months' target values.
- Do not recalculate older months automatically.

When an older month is reimported from Google Sheets:

- Recalculate that imported month's target using the employee's current weekly target.
- Recalculate its closing balance.
- Propagate only the resulting opening hour-account balance to later months.
- Leave later months' `target_working_hours` unchanged.

## Manual spreadsheet entries

For paid-absence types such as `Urlaub`, `Krankenstand`, `Feiertag`, and `Extern`, calculate credited hours from the employee's agreement:

```text
weekly_target_hours / work_days_per_week
```

Round the result to two decimal places. `Frei` continues to write zero hours.

Relevant implementation areas:

- `docs/architecture/main-logic/sheets-preview-logic.md`
- `src/backend/workspace/google_sheets_client.py` (`parse_manual_entry`)
- employee registration and employee details endpoints and forms

## Tests

The implementation must include tests covering:

- migration backfill and preservation of existing monthly values;
- monthly conversion and `ROUND_HALF_UP` behavior;
- weekly-hours and work-days validation boundaries;
- registration and employee editing;
- automatic current-month recalculation and later balance propagation;
- older-month reimport behavior;
- employee-specific paid-absence hours in manual entries.
