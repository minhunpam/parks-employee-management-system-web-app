# Tasks

## 1. Calendar-week row rendering

- [x] 1.1 Add calendar-week boundary and week-of-month calculation to the employee detail rendering, and verify separators appear after Sunday and month-end partial weeks with correct numbering.
- [x] 1.2 Ensure separator rows span the table, are labeled “End of week <n>”, and do not expose correction actions; verify existing daily rows and correction controls remain unchanged.

## 2. Tests

- [x] 2.1 Add frontend tests for a month beginning mid-week, an in-month Sunday boundary, a month ending mid-week, and a calendar week crossing an ISO week/year boundary; verify separator placement and week numbering.
- [x] 2.2 Run the frontend Jest suite from `src/frontend` and verify all tests pass.
