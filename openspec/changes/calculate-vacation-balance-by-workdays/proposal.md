# Proposal

## Why

The current schedule-change recalculation incorrectly carries the previous month's closing vacation balance directly into the current month. When the workday policy changes during a year, the already-earned balance must be converted to the new policy and the remaining months must accrue under the new policy. The applicable workday policy also needs to be retained on each monthly record so recalculation can compare the current month with the previous policy.

## What Changes

- Keep the existing capped annual entitlement and registration-baseline behavior.
- Add the applicable `work_days_per_week` value to each `EmployeeMonth`.
- Preserve the workday policy on historical monthly records.
- Recalculate vacation balances with monthly accrual only when a current schedule change triggers recalculation.
- Convert the balance earned under the previous policy to the new policy instead of copying the previous closing balance.
- Add the new policy's monthly entitlement to the current and subsequent months while preserving recorded usage.
- Leave monthly records before the changed month unchanged.
- Keep normal spreadsheet month imports compatible with their existing behavior; imports do not independently switch the system to the new accrual calculation.
- Add regression coverage for schedule changes after ten months with and without vacation usage.

## Capabilities

### New Capabilities

- `employee-vacation-entitlement`: Determine annual vacation entitlement and schedule-change vacation balances from working-day policies.

### Modified Capabilities

<!-- No existing vacation-entitlement capability is present in the project specs. -->

## Impact

- Affects `EmployeeMonth` persistence, schedule-change recalculation, yearly balance updates, and related migrations.
- Affects employee and workspace tests and employee-management architecture documentation.
- Does not change the normal imported-month calculation unless a schedule change explicitly triggers forward recalculation.
