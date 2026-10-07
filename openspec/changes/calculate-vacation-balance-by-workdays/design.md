# Design

## Context

See `proposal.md` for the motivation and `specs/employee-vacation-entitlement/spec.md` for the behavioral contract. The current implementation stores monthly balances but not the workday policy that produced them, and schedule changes currently carry the previous closing balance directly into the current month.

## Goals / Non-Goals

**Goals:**

- Preserve the applicable workday policy on every monthly record.
- Apply the conversion and monthly-accrual algorithm only during explicit schedule-change recalculation.
- Preserve all monthly records before the changed month.
- Recalculate the current month, later months, and current yearly balance from the latest policy.
- Keep normal spreadsheet imports on their existing calculation path.
- Continue supporting capped entitlements, registration baselines, carry-over, and signed balances.

**Non-Goals:**

- No schedule-history table.
- No independent accrual recalculation for an ordinary month import.
- No rewriting of prior monthly records after a schedule change.
- No change to vacation usage input semantics or public API field names.

## Decisions

### Store the applicable policy on `EmployeeMonth`

Add a validated `work_days_per_week` value to `EmployeeMonth`. Historical imports use the registration baseline for pre-registration months; the registration month and later months use the current employee value. When a current schedule changes, the changed month and existing subsequent months receive the latest current value, while prior records remain immutable.

This avoids trying to infer a historical policy from the employee's current value. A schedule-history table was considered but is unnecessary because the contract explicitly preserves only monthly policy snapshots and uses the latest value for forward recalculation.

### Recalculate conversion from the preceding period, not by copying closing balance

For a change in the current month, determine the prior policy from the previous monthly record and the new policy from the employee's current value. Let `old_entitlement` and `new_entitlement` be their capped annual entitlements, and let `elapsed_months` be the number of months completed before the changed month. The converted prior balance is:

```text
(old_entitlement - vacation_used_before_change)
× elapsed_months / 12
× new_entitlement / old_entitlement
```

The current month's balance is then completed with the new policy's monthly accrual, less current-month usage. Each subsequent month adds `new_entitlement / 12` and subtracts that month's recorded usage. This directly supports the ten-month examples and avoids treating a prior closing balance as if it were already denominated in the new policy.

If no prior monthly record exists, the recalculation starts from the current year's applicable entitlement and carry-over using the new policy. If the old entitlement is zero, the conversion ratio is not applied; the new policy's accrual becomes the starting balance.

### Keep import behavior separate

The spreadsheet synchronization path continues to calculate an imported month using its existing behavior. It records the applicable monthly workday value but does not invoke the schedule-change conversion merely because a month was imported. This preserves compatibility and limits the new algorithm to the event that requires it.

### Rebuild yearly balance from the recalculated monthly result

After recalculating the current and later monthly records, update the current `EmployeeYear` from the resulting current-year balance and recorded usage. At a year boundary, preserve the signed closing balance as carry-over and start the next year's available balance with its entitlement plus carry-over.

## Risks / Trade-offs

- [Risk] Persisted monthly balances may use integer database fields while the accrual examples produce fractions. → Mitigation: define and test the existing persistence precision/rounding policy before implementation; keep calculation precision until persistence.
- [Risk] A missing previous monthly record makes the old policy unavailable. → Mitigation: use the registered/current baseline applicable to the earliest available month and test missing-month paths.
- [Risk] Updating future stored records can overwrite policies that were manually imported with different historical context. → Mitigation: only update records at or after the explicit schedule-change month; never update prior records.
- [Risk] Repeated schedule changes could compound conversions. → Mitigation: use the latest current value together with the stored previous-month policy and recalculate the forward chain from the current month each time.
- [Risk] Normal imports and schedule changes could apply different balance rules. → Mitigation: keep the import path separate and add integration tests for both entry points.

## Migration Plan

1. Add the monthly workday field with a temporary safe default.
2. Backfill existing monthly records from the applicable employee policy, using the registered baseline for pre-registration months and the current value otherwise.
3. Enforce the workday range and remove any temporary migration-only default if appropriate.
4. Deploy the schedule-change recalculation and tests.
5. Validate ten-month conversion, usage, missing-month, carry-over, repeated-change, and normal-import scenarios. Roll back through the schema migration and application deployment if required.
