# Employee register

## Purpose

The employee register page lets a manager create an employee record before the employee enters the monthly hours workflow. It collects identity, employment status/dates, and the working agreement used to calculate monthly targets.

## Endpoint and integration

- **Page:** `employees:employee-register`
- **Create request:** `employees:register` via the registration module.
- **Cancel:** returns to `employees:employee-dashboard`.
- The page exposes both URLs through `#employee-registration-page` data attributes. Do not rename the element or its data attributes without updating `employee-registration.js`.

## Page structure

1. **Global header**
   - Black 64px navigation bar.
   - NVIDIA Green PARKS wordmark at left.
   - Employee management context and Employee dashboard link at right.
2. **Breadcrumb bar**
   - Soft gray strip containing `Employees / Register employee`.
3. **Dark page intro**
   - Eyebrow: `Employee records`.
   - H1: `Register a new employee.`
   - Supporting copy explains that the working agreement drives monthly hours.
4. **Registration content**
   - Two-column desktop layout: form (wide) and guidance aside (narrow).
   - Single-column layout below the desktop breakpoint.
5. **Footer**
   - Black compact footer with PARKS identity and product context.

## Registration form

The form is a bordered white technical panel with a 12px green corner square. It uses three field groups:

### Personal information

- First name — required text input, `given-name` autocomplete.
- Last name — required text input, `family-name` autocomplete.
- Email — required email input, `email` autocomplete. Server-side email errors are surfaced through the existing JavaScript validity handling.

### Employment

- Working status — required select with `Active` and `Archived` options.
- Employment start date — required date input. The existing client logic rejects future dates and a date equal to the end date.
- Employment end date — optional date input. The existing client logic rejects past dates and a date equal to the start date.

### Working agreement

- Work days per week — required number input, constrained to 1–7, default `5`.
- Monthly target hours — required number input, minimum `0`, two-decimal step, default `173.00`.

The form preserves the existing IDs and names because the JavaScript payload is generated from `FormData`.

## Actions and feedback

- **Register employee:** solid NVIDIA Green primary button, 44px minimum height. Submits JSON through the existing module and resets the form after a successful response.
- **Cancel:** transparent secondary button with a 2px green border. Navigates to the [employee dashboard](/home/minhun/dev/parks/parks-employee-management-system-web-app/docs/design/pages/employee-dashboard.md) without submitting.
- **Status message:** persistent reserved space beneath the actions, with a green left rule and `role="status"` / `aria-live="polite"`. It communicates successful responses and unexpected request failures.
- Native required, type, min/max, and step constraints remain enabled for browser validation. Focus uses a 2px NVIDIA Green border and visible focus ring.

## Guidance aside

The gray bordered aside uses the standard corner square and explains three manager checks: use a unique email, verify the working agreement, and only add an end date when known. It is supporting content, not an additional action.

## Visual rules

- Canvas: white; intro/header/footer: black; guidance: `#f7f7f7`.
- Accent: NVIDIA Green `#76b900`; pressed primary state `#5a8d00`.
- Borders: `#cccccc`; muted copy: `#757575`; validation/error copy: `#e52020`.
- NVIDIA/Arial-style sans-serif, bold weight for labels and headings.
- 2px maximum radius; this page intentionally uses angular rectangular controls.
- No card shadows. Separation comes from hairline borders and section rules.
- Form controls are 44px high and action controls have at least 44px touch height.

## Responsive behavior

- Desktop: form and aside use a wide/narrow grid within the 1280px content container.
- Small screens: the grid becomes one column, field pairs stack, and the action row becomes a full-width-friendly vertical arrangement.
- Header context text hides on narrow screens while the dashboard link remains available.
- Content gutters reduce from 32px to 24px on small screens.

## Accessibility

- The document has one page-level H1 and field groups use `fieldset`/`legend`.
- Every control has an explicit label; required indicators are supplemental to the native `required` behavior.
- Status updates are announced politely without interrupting the manager.
- Keyboard focus is visible on links, inputs, selects, and buttons.
- Color is not the only source of meaning: labels, text, native validation, and borders communicate state.
