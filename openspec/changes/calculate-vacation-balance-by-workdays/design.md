# Design

## Context

See `proposal.md` for the motivation and behavioral scope. Employees store a current `work_days_per_week` value, while monthly and yearly vacation balances are persisted separately. Historical months may be imported after registration, so the registration-time workday value must be preserved independently. Existing balance fields use non-negative integer types even though the domain permits deficits.

## Goals / Non-Goals

**Goals:**

- Apply `min(work_days_per_week * 5, 25)` consistently to new and recalculated yearly entitlements.
- Preserve `registered_work_days_per_week` as the baseline for pre-registration months.
- Allow correction of that baseline until the first pre-registration month is imported.
- Recalculate the current month and forward monthly chain when the current schedule changes.
- Recalculate the current `EmployeeYear` immediately.
- Preserve stored monthly records before the current month.
- Support negative balances and negative carry-over.
- Repair legacy fixed-entitlement records through an idempotent migration.

**Non-Goals:**

- No schedule-history table or reconstruction of every prior schedule.
- No rewriting of past monthly records when the current schedule changes.
- No change to vacation usage input semantics or API field names.

## Decisions

### Centralize the capped entitlement calculation

Use one domain calculation:

```text
annual_allowed_vacation_days = min(work_days_per_week * 5, 25)
```

Use it for new `EmployeeYear` records, schedule-change recalculation, and legacy repair. The cap keeps six- and seven-day schedules at the 25-day maximum.

### Store and lock the registration baseline

Add `registered_work_days_per_week` to `Employee`. During registration, copy the submitted workday value into both the registered and current fields. Existing employees receive a data-migration backfill from their current `work_days_per_week`.

A pre-registration month is an `EmployeeMonth` whose `(year, month)` is earlier than the employee registration month derived from `created_at`. Historical imports use the registered value for these months. The registration month and later months use the current value.

The registered value remains editable while no pre-registration month exists. Once one exists, the backend rejects changes to the registered value; the frontend disables the control and explains why. The registration confirmation dialog warns that later imports of previous months use this baseline and current schedule changes do not rewrite those imported records.

### Apply the latest current schedule forward

When `work_days_per_week` changes, update the employee and recalculate the current calendar month's vacation opening and closing balances. Recalculate subsequent monthly balances from that point forward and update the current year's annual entitlement and balance. Do not modify earlier monthly records and do not retain current schedule history. A later schedule change repeats the same process using the newest value.

The current month's opening balance is derived from the preceding month's stored closing balance where available, or from the recalculated yearly entitlement plus carry-over when no preceding month exists. Its closing balance is derived after applying that month's recorded vacation usage. Subsequent months receive the propagated balance while retaining their recorded usage.

### Use signed integer balance fields

Change these fields to signed integer database fields:

- `EmployeeYear.carried_over_vacation_days`
- `EmployeeYear.vacation_balance`
- `EmployeeMonth.opening_vacation_balance`
- `EmployeeMonth.closing_vacation_balance`

Keep `annual_allowed_vacation_days` and `vacation_days_used` non-negative. A negative yearly closing balance becomes negative carry-over for the next year.

### Repair legacy records once

Add a data migration that identifies legacy yearly records using the fixed 25-day entitlement, applies the capped entitlement, preserves carry-over, and rebuilds affected monthly and yearly derived balances from recorded vacation usage. The migration must be idempotent and must not be used for later schedule edits.

## Risks / Trade-offs

- [Risk] Without schedule history, repeated current-schedule changes cannot reconstruct earlier current-schedule periods. → Mitigation: explicitly use the latest value only and preserve past monthly records.
- [Risk] A registered baseline could be changed after historical import and corrupt past data. → Mitigation: enforce the lock in the backend based on the existence of a pre-registration month.
- [Risk] Forward recalculation may change future stored balances based on the new current-month opening balance. → Mitigation: keep prior months immutable and test propagation boundaries.
- [Risk] Existing positive-integer columns may contain only non-negative data but future calculations may produce deficits. → Mitigation: use a schema migration and test negative monthly, yearly, and carry-over values.
- [Risk] Legacy records may have incomplete monthly data. → Mitigation: use available recorded usage, preserve carry-over, make the migration idempotent, and test missing-month paths.

## Migration Plan

Deploy schema migrations for the registered baseline and signed balance fields. Backfill `registered_work_days_per_week` from `work_days_per_week` for existing employees. Run the legacy data migration after the schema migration, then validate representative reduced-schedule, capped-schedule, historical-import, carry-over, and negative-balance records. Back up the database before deployment; restoring the backup is the rollback path for corrected data.
