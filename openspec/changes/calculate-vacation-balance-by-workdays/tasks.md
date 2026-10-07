# Tasks

## 1. Entitlement and balance model changes

- [x] 1.1 Add and test the centralized capped entitlement calculation `min(work_days_per_week * 5, 25)` for 1–7 working days per week.
- [x] 1.2 Change yearly and monthly vacation balance fields, including carried-over vacation days, to signed integer database fields; add schema migration and tests proving negative values persist.
- [x] 1.3 Add `registered_work_days_per_week`, backfill existing employees from `work_days_per_week`, and verify the migration preserves each employee's current value.
- [x] 1.4 Initialize new employee-associated yearly and first monthly records with the capped entitlement and verify reduced, five-day, six-day, and seven-day schedules.

## 2. Registration and historical imports

- [x] 2.1 Copy the registration workday value into both current and registered fields; verify registration tests.
- [x] 2.2 Use the registered baseline for imported months before the registration month and the current value for the registration month and later; verify historical-import tests.
- [x] 2.3 Allow registered-workday corrections before any pre-registration month exists and reject them afterward in the backend; verify both editable and locked cases.
- [x] 2.4 Add the registration confirmation dialog with the agreed heading and historical-import warning; verify the dialog appears before registration is finalized.

## 3. Schedule-change recalculation

- [x] 3.1 Update employee schedule edits to recalculate the current month's opening and closing vacation balances, the current `EmployeeYear`, and subsequent months while leaving past months unchanged; verify with backend tests.
- [x] 3.2 Ensure repeated schedule changes use only the latest current workday value and do not create schedule-history records; verify a multi-change regression test.
- [x] 3.3 Propagate negative current-month balances and negative carry-over through subsequent months and years; verify deficit scenarios in employee and workspace tests.

## 4. Legacy data repair and integration

- [x] 4.1 Add an idempotent migration that repairs legacy fixed-25-day yearly entitlements using the capped formula; verify four-day records become 20 days while five-day records remain 25 days.
- [x] 4.2 Rebuild affected monthly and yearly balances from recorded usage and preserved carry-over, including negative results and missing-month paths; verify repeated migration execution is stable.
- [x] 4.3 Update spreadsheet summary synchronization to use the capped entitlement, registered baseline, and signed vacation balances without reintroducing fixed positive-only assumptions; verify relevant workspace tests.
- [x] 4.4 Update employee-management architecture documentation to describe the cap, registration baseline, lock rule, forward-only schedule recalculation, latest-value behavior, and signed balances; verify the documentation matches implemented behavior.
- [x] 4.5 Run the relevant Django employee and workspace test suites and verify existing five-day balance-chain scenarios remain passing.
- [x] 4.6 Run `openspec validate calculate-vacation-balance-by-workdays --type change` and verify all artifacts and scenarios validate successfully.

## 5. Correct schedule-change accrual recalculation

- [x] 5.1 Add `EmployeeMonth.work_days_per_week`, its validation and schema migration, and backfill existing monthly records from the registration baseline/current policy; verify historical and registration-month values.
- [x] 5.2 Replace direct previous-closing-balance propagation during schedule changes with the policy-conversion and monthly-accrual algorithm; verify the ten-month no-usage example reaches 25 days.
- [x] 5.3 Add usage-aware conversion and precision/rounding behavior; verify the ten-month, two-days-used example reaches `275/12` before persistence rounding.
- [x] 5.4 Recalculate current and subsequent month records with the latest policy while preserving earlier records; verify repeated schedule changes, negative balances, carry-over, and missing-month paths.
- [x] 5.5 Keep normal spreadsheet imports on their existing balance path while recording monthly workday policy; verify imports do not independently trigger schedule-change accrual.
- [x] 5.6 Update employee-management architecture documentation and relevant integration tests to describe the monthly policy snapshots and schedule-change-only accrual behavior.
- [x] 5.7 Run the Django employee/workspace suites, frontend tests, and `openspec validate calculate-vacation-balance-by-workdays --type change`; verify all revised scenarios pass.
