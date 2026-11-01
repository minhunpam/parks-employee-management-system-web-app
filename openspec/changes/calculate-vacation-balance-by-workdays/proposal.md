# Proposal

## Why

The employee details endpoint correctly recalculates the current month when the workday schedule changes, but the page only receives a success message. Because `registered_work_days_per_week` is read-only in the form, the displayed value can remain stale after the backend updates it during a valid current-month edit.

## What Changes

- Keep `registered_work_days_per_week` permanently read-only in the employee details UI, including when no historical month has been imported and the current month exists.
- Return the persisted employee workday values from a successful details update response.
- Update the read-only registered-workday field and its change-detection baseline from the JSON response without a full page reload.
- Preserve the existing schedule-change recalculation and registration-baseline rules.
- Skip vacation accrual/conversion when the current month has no preceding monthly record.
- Correct whole-day vacation balance rounding.
- Add backend and frontend regression coverage for the response, display synchronization, and missing-previous-month behavior.

## Capabilities

### New Capabilities
- `employee-vacation-entitlement`: Determine annual vacation entitlement and schedule-change vacation balances from working-day policies.

### Modified Capabilities
- None. The existing entitlement and registration behavior is preserved; this change adds client synchronization for already-defined behavior.

## Impact

- Affects `src/backend/employees/views.py` and employee details endpoint response data.
- Affects `src/frontend/static/scripts/employees/employee-details.js` and the read-only field behavior on the employee details page.
- Adds backend endpoint and frontend interaction tests.
- Does not change the public field name, schedule-change calculation, migration behavior, or archive flow.
