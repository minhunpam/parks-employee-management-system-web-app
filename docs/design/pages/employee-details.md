# Employee Details

## Purpose
- The Employee Details page lets a manager review and update one employee's personal information, employment details, and working agreement.
- The page also lets a manager archive an employee without deleting the employee or their historical monthly and yearly records.

## Endpoint and integration
- **Page:** `employees:employee-details`
- **URL:** `/employees/employee-dashboard/<employee_id>`
- The first name in the Employees table links to the matching employee details page.
- The page exposes these values through `#employee-details-page` data attributes:
  - `data-dashboard-url` — destination for the dashboard and Cancel action
  - `data-details-url` — endpoint used to load and update the employee
- The page uses `employee-details.js` for change detection, updates, archive handling, and status feedback.

## Page structure
```text
Employee Details
├── Global header
├── Breadcrumb bar
├── Dark page intro
├── Employee details form
│   ├── Personal information
│   ├── Employment
│   └── Working agreement
├── Danger zone
└── Footer
```

## Header and introduction
- Use the existing project design system:
  - black navigation and hero surfaces
  - white heading text
  - NVIDIA Green (`#76b900`) eyebrow, wordmark, and accents
  - angular layout with no card shadows
  - maximum content width of approximately 1280px
- The global header contains:
  - PARKS wordmark linking to the home page
  - Employee management context, hidden on narrow screens
  - Employee dashboard link
- The breadcrumb displays:
```text
Employees / Employee details
```
- The dark page intro contains:
```text
Employee records
Manage employee details.
Update the employee profile and working agreement without changing historical records.
```

## Employee details form
- The form is a bordered white technical panel with a 12px NVIDIA Green corner square.
- Required fields are marked with an asterisk. The form uses the existing field IDs and names because the JavaScript payload is generated from `FormData`.

### Personal information
- First name — required text input with `given-name` autocomplete.
- Last name — required text input with `family-name` autocomplete.
- Email — required email input with `email` autocomplete.

### Employment
- Working status — required select with `Active` and `Archived` options.
- Employment start date — required date input.
- Employment end date — optional date input.

### Working agreement
- Work days per week — required number input constrained to `1`–`7`.
- Monthly target hours — required number input with a minimum of `0` and a two-decimal step.
- Supporting copy states that changes apply to future monthly records only.

## Actions and feedback
- **Save changes:** disabled until a form field differs from its original value. Sends the complete form as a JSON `PATCH` request.
- **Cancel:** returns to the Employee Dashboard without submitting changes.
- **Status message:** reserved space beneath the actions with a green left rule, `role="status"`, and `aria-live="polite"`. It communicates saving, success, validation errors, and unexpected request failures.
- Successful updates display:
```text
Employee details updated successfully.
```
- Server-side validation errors are displayed in the status area.

## Archive employee
- The Danger zone appears below the form with a red border and pale red background.
- The archive action is available for active employees. It is hidden when the employee is already archived.
- Clicking **Archive employee** asks for confirmation:
```text
Archive this employee? Their history will be preserved and their employment end date will be set to today.
```
- After confirmation, the page sends `{ "action": "archive" }` through the same `PATCH` endpoint.
- Archiving:
  - changes `working_status` to `archived`;
  - sets `employment_end_date` to the current date;
  - preserves the employee and historical records;
  - returns the manager to the Employee Dashboard after success.

## Data endpoint
- `GET /employees/employee-dashboard/<employee_id>` renders the page for the selected employee.
- `PATCH /employees/employee-dashboard/<employee_id>` updates the employee or archives them.
- Requests require authentication and include the CSRF token.
- A normal update accepts:
```text
first_name
last_name
email
working_status
employment_start_date
employment_end_date
work_days_per_week
monthly_target_hours
```
- The backend validates the submitted employee with `full_clean()` before saving. Invalid dates, duplicate/invalid email values, invalid working status, and other model validation errors return a 400 response with error details.

## Visual rules
- Canvas: white; navigation, intro, and footer: black.
- Accent: NVIDIA Green `#76b900`; pressed primary state `#5a8d00`.
- Borders: `#cccccc`; muted copy: `#757575`; validation/error copy: `#e52020`.
- Form fields and action controls use a minimum 44px height.
- Controls use angular rectangular geometry with a maximum 2px radius.
- No shadows; separation comes from hairline borders and section rules.
- The archive action uses the existing semantic error colors and is visually separated from normal editing actions.

## Responsive behavior
- Desktop content uses the 1280px container and a wide form column.
- On small screens, field pairs stack into one column and action controls stack vertically while remaining touch-friendly.
- Header context text hides on narrow screens; the dashboard link remains available.
- Content gutters reduce from 32px to 24px on small screens.

## Accessibility
- The document has one page-level H1.
- Form fields use explicit labels, and related controls are grouped with `fieldset` and `legend`.
- Required indicators supplement native `required` validation rather than replacing it.
- Status updates are announced politely without interrupting the manager.
- Links, inputs, selects, and buttons have visible keyboard focus states.
- Archive confirmation is explicit, and color is supported by labels and explanatory text rather than used as the only source of meaning.
