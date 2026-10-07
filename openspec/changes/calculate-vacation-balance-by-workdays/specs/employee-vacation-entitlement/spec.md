# Spec Delta

## Purpose

This capability ensures annual vacation entitlement and balances reflect the employee's working-day schedule while preserving historical monthly records and supporting deficits.

## ADDED Requirements

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

### Requirement: Schedule changes recalculate the current year forward
When an employee's current working days change, the system SHALL recalculate the current month, subsequent months, and the current yearly balance using the latest value, while leaving past monthly records unchanged.

#### Scenario: Current-month schedule change
- **WHEN** an employee changes from 5 to 4 working days per week
- **THEN** the current month's vacation opening and closing balances, the current yearly record, and subsequent monthly balances are recalculated using a 20-day annual entitlement

#### Scenario: Past months remain unchanged
- **WHEN** the schedule changes during the year
- **THEN** monthly vacation balances before the current month retain their stored values

#### Scenario: Multiple schedule changes
- **WHEN** an employee changes schedule more than once in the same year
- **THEN** the most recently saved workday value is used for the current month, subsequent months, and current yearly calculation, without storing schedule history

### Requirement: Vacation balances support deficits
The system SHALL allow vacation balance and carried-over balance values to be negative when vacation usage exceeds available entitlement.

#### Scenario: Negative monthly balance
- **WHEN** an employee uses more vacation days than the month's opening balance
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
