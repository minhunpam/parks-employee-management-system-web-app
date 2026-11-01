# Spec Delta

## Purpose

This capability ensures vacation entitlement reflects the employee's workday policy and that schedule changes recalculate only the affected period using transparent monthly accrual and preserved historical policies.

## ADDED Requirements

### Requirement: Monthly records preserve their workday policy
Each monthly employee record SHALL retain the workday policy applicable to that month.

#### Scenario: Imported historical month stores its baseline policy
- **WHEN** a month before registration is imported
- **THEN** the monthly record stores `registered_work_days_per_week`

#### Scenario: Registration month stores the current policy
- **WHEN** the registration month or a later month is created
- **THEN** the monthly record stores the employee's current `work_days_per_week`

### Requirement: Schedule-change recalculation uses monthly accrual
When a current workday policy changes, the system SHALL convert the previously earned balance to the new policy and accrue the new policy monthly from the changed month forward.

#### Scenario: Ten months under four days followed by two months under five days
- **WHEN** an employee has a 20-day annual entitlement for the first ten months and changes to a 25-day entitlement in November without vacation usage
- **THEN** the recalculated balance is `20 × 10/12 × 25/20 + 25 × 2/12 = 25` days, subject to the system's persisted precision policy

#### Scenario: Ten months under four days with two used days
- **WHEN** an employee has a 20-day annual entitlement for the first ten months, uses 2 vacation days, and changes to a 25-day entitlement in November
- **THEN** the recalculated balance is `18 × 10/12 × 25/20 + 25 × 2/12 = 275/12` days, subject to the system's persisted precision policy

### Requirement: Schedule changes recalculate only the current period forward
A schedule-change recalculation SHALL update the changed month, later monthly records, and the current yearly balance, while preserving monthly records before the changed month.

#### Scenario: Previous months remain unchanged
- **WHEN** the current schedule changes during a year
- **THEN** monthly workday policies, usage, opening balances, and closing balances before the changed month remain unchanged

#### Scenario: Later months use the latest policy
- **WHEN** the employee changes schedule more than once
- **THEN** the changed month and subsequent months use the latest saved policy without creating schedule-history records

### Requirement: Normal imports retain their existing calculation mode
The monthly accrual recalculation SHALL run only when a schedule change explicitly triggers it.

#### Scenario: Month import without a schedule change
- **WHEN** a spreadsheet month is imported and the employee's schedule has not changed
- **THEN** the import uses the existing month-import balance behavior and does not independently apply the schedule-change conversion algorithm

#### Scenario: Schedule change followed by month import
- **WHEN** a schedule change has recalculated the forward chain and a later month is imported
- **THEN** the imported usage is incorporated without changing preserved months before the schedule change

### Requirement: Missing previous monthly records do not trigger accrual
When the current monthly record has no preceding `EmployeeMonth` for the employee, a schedule update SHALL not apply vacation balance conversion or monthly accrual.

#### Scenario: Schedule changes without a previous month
- **WHEN** a manager changes `work_days_per_week` and the current month exists but no earlier monthly record exists
- **THEN** the current month's existing vacation opening and closing balances remain unchanged, while non-vacation employee update behavior continues normally

### Requirement: Employee details updates synchronize read-only workday values
A successful employee details update SHALL return the persisted current and registered workday values, and the details page SHALL display the returned registered value while keeping its control read-only.

#### Scenario: Current-month schedule update refreshes the registered value
- **WHEN** a manager saves a valid schedule update while the current month exists
- **THEN** the response contains the persisted `work_days_per_week` and `registered_work_days_per_week`, and the page updates the registered-workday field to the returned value without a full page navigation

#### Scenario: Registered workday field remains read-only
- **WHEN** the employee details page is rendered or a successful update is completed
- **THEN** the `registered_work_days_per_week` control remains disabled/read-only and is not treated as an editable submitted field

## MODIFIED Requirements

### Requirement: Annual vacation entitlement is capped at 25 days
The system SHALL calculate annual allowed vacation days as `min(work_days_per_week * 5, 25)`.

#### Scenario: Reduced schedule entitlement
- **WHEN** an employee works 1, 2, 3, 4, or 5 days per week
- **THEN** annual entitlement is respectively 5, 10, 15, 20, or 25 days

#### Scenario: Six- or seven-day schedule entitlement
- **WHEN** an employee works 6 or 7 days per week
- **THEN** annual entitlement is 25 days

### Requirement: New yearly and monthly records use capped entitlement
New yearly records SHALL use the employee-specific capped entitlement, and the first monthly opening balance SHALL include that entitlement and applicable carry-over.

#### Scenario: New year for a four-day employee
- **WHEN** a yearly record is created for a four-day employee with no carry-over
- **THEN** annual entitlement and initial yearly balance are 20 days, and the first monthly opening balance is 20 days

#### Scenario: New year with carry-over
- **WHEN** a yearly record is created for a three-day employee with 4 carried-over days
- **THEN** annual entitlement is 15 days and available balance includes the 4 carried-over days

### Requirement: Registration stores a historical workday baseline
When an employee is registered, the system SHALL store the entered workday value as both the current and registered workday value.

#### Scenario: Registration initializes both workday values
- **WHEN** an employee is registered with 4 workdays per week
- **THEN** `work_days_per_week` and `registered_work_days_per_week` are both 4

#### Scenario: Registration warning is shown
- **WHEN** the employee registration form is submitted
- **THEN** a confirmation dialog asks "Are you sure every fields were correctly entered?" and explains that importing previous months will use the registered workday value and later changes will not affect those months

### Requirement: Historical month imports use the registered baseline
A month imported before the employee's registration month SHALL use `registered_work_days_per_week`, while the registration month and later months SHALL use the current `work_days_per_week`.

#### Scenario: Previous month is imported after registration
- **WHEN** an employee is registered in October and a September CSV is imported
- **THEN** the September monthly record uses `registered_work_days_per_week`

#### Scenario: Registration month uses current agreement
- **WHEN** an employee is registered in October and the October monthly record is created
- **THEN** the October record uses the current `work_days_per_week`

### Requirement: Registered workday baseline can be corrected before historical import
The system SHALL allow `registered_work_days_per_week` to change while no `EmployeeMonth` exists before the employee's registration month.

#### Scenario: Correct registration mistake before import
- **WHEN** the manager corrects the registered workday value before importing any previous month
- **THEN** the corrected value is saved and is used for later previous-month imports

#### Scenario: Historical baseline is locked after import
- **WHEN** an `EmployeeMonth` exists before the employee's registration month
- **THEN** attempts to change `registered_work_days_per_week` are rejected and the stored baseline remains unchanged

### Requirement: Vacation balances support deficits
The system SHALL allow vacation balance and carried-over balance values to be negative when vacation usage exceeds available entitlement.

#### Scenario: Negative monthly balance
- **WHEN** an employee uses more vacation days than the month's recalculated opening balance
- **THEN** the monthly closing vacation balance is negative

#### Scenario: Negative carry-over
- **WHEN** a year's final vacation balance is negative
- **THEN** the following year's carried-over vacation days may be negative and are included in its available balance

### Requirement: Legacy vacation records can be repaired by an explicit migration
An explicit idempotent migration SHALL repair legacy records initialized with the fixed 25-day entitlement using the capped entitlement rule and recorded usage.

#### Scenario: Repair a four-day employee's legacy year
- **WHEN** a four-day employee has a legacy annual entitlement of 25 days
- **THEN** the migration changes the entitlement to 20 days and recalculates derived balances

#### Scenario: Repeatable repair
- **WHEN** the repair migration runs more than once
- **THEN** the second run does not change already-corrected records
