# Proposal

## Why

Vacation entitlement currently uses a fixed five-day assumption and schedule changes do not consistently update current-year balances. Historical months imported after registration also need a stable registration-time workday value so later edits cannot corrupt their interpretation.

## What Changes

- Calculate annual entitlement as `min(work_days_per_week * 5, 25)` days.
- Initialize new yearly and monthly vacation balances from the employee-specific capped entitlement.
- When `work_days_per_week` changes, recalculate the current month, subsequent months, and the current `EmployeeYear`; leave past months unchanged.
- Use the latest workday value when the schedule changes multiple times; do not store schedule history for current/future recalculation.
- Store `registered_work_days_per_week` as the baseline for months imported before the employee's registration month.
- Allow the registered workday value to be corrected until a previous-month record exists, then lock it.
- Show a registration confirmation dialog explaining the effect of importing previous months.
- Allow negative vacation balances and negative carried-over vacation days.
- Add a one-time, idempotent migration to repair legacy records initialized with the fixed 25-day entitlement.

## Capabilities

### New Capabilities

- `employee-vacation-entitlement`: Determine annual vacation entitlement and vacation balances from an employee's working days per week.

### Modified Capabilities

<!-- No existing vacation-entitlement capability is present in the project specs. -->

## Impact

- Affects employee models, registration, schedule-update handling, and monthly/yearly balance recalculation.
- Affects historical month imports, spreadsheet summary synchronization, and legacy data migration.
- Requires database migrations for the registered workday field and signed vacation balance fields.
- Requires frontend confirmation and backend lock validation.
- Requires tests for capped entitlement, schedule changes, registration baselines, historical imports, repeated changes, legacy repair, negative balances, carry-over, and balance propagation.
