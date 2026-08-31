# PDF Export and Delivery Logic

## Purpose
- The PDF export workflow creates monthly reports from the synchronized Google Sheets data and delivers them to the appropriate recipients. It supports two different report types:
  1. One combined summary report for configured restaurant managers.
  2. One daily-entry report for each employee represented in the selected month.
- The reports are generated and reviewed in PARKS. Sending is a separate, explicit action.

## Source data and readiness
- Google Sheets remains the source of truth for daily operational entries. PDF exports must use the same synchronized data that is displayed by the Sheets preview page.

- Exporting is allowed only when:
  - The selected month has been imported successfully.
  - The relevant Google Sheets data has been synchronized successfully.
  - There are no unresolved import errors.
  - There are no unresolved synchronization errors.

- If the selected month is not valid or contains unresolved errors, PDF generation must be blocked. The manager should receive an actionable explanation instead of being allowed to create potentially incomplete legal or management documents.
- The summary and employee reports must be generated from the same synchronized snapshot so that they describe the same period and data state.

## Export folder structure

- The configured Google Drive root folder contains an `Export` folder. The export process prepares the month folder using the same month/year structure as the import workflow:
```text
root_folder/
└── Export/
    └── {zero-padded month}_{year}/
        └── generated PDF files
```

-For example:
```text
Export/06_2026/
```

The `Export` folder and the selected month folder are created when they do not exist. The current workspace preparation is handled by `prepare_csv_import_and_export_folder` in the Google Drive client because the import and export periods use the same configured month context.

## PDF types
### Manager summary report
- The manager report is one combined PDF for the selected month. It reproduces the current summary table as-is:
  - Every existing summary column is included.
  - Existing values and column meaning are preserved.
  - No summary columns are selectively removed for the export.
  - The report contains the employees represented in the selected month’s synchronized records.

- The report is not generated once per manager. One summary PDF is generated and the same file is sent separately to every configured manager recipient.

The filename is:
```text
Monatsübersicht_{German month}_{year}_EXPORT.pdf
```
Example:
```text
Monatsübersicht_Juni_2026_EXPORT.pdf
```

### Employee daily-entry report
- An employee report is generated separately for each employee represented in the selected month’s records. It contains the daily rows shown in the Sheets preview employee detail view.

The report contains only these columns:
```
| Date | Shift start | Pause start | Pause end | Shift end | Pause time | Shift total time | Type |
```

> **The report must not contain the internal `Warnings` column. Warnings are useful for operational review but should not appear in these reports because the PDFs may be presented to an authority as legal working-time documentation.**

> **By default, the employee report includes every calendar day in the selected month. Days without an entry remain in the report with blank daily values or the corresponding ordinary non-working-day representation from the synchronized data. A future export option may allow managers to omit rows without entries, but that is not part of the current behavior.**

The employee filename preserves the imported CSV naming convention and adds `_EXPORT` before the file extension:

```
Schicht_{employee name}_{German month}_{year}_EXPORT.pdf | Schicht_Angelina_Juni_2026_EXPORT.pdf
```

The employee name must follow the same employee-matching rules used by the import and Sheets preview workflows. The filename must not cause an ambiguous employee to receive another employee’s report.

## Which employees are included

The selected month, rather than the employee’s current working status, determines historical inclusion.

For example, an employee who worked in June and was archived in July must still appear in the June summary and must still have a June employee report.

The current rule is that employees represented by records in the selected month’s synchronized data are included. Employees without records for the selected month are excluded. The precise business treatment of a month containing only paid absence records should remain aligned with the monthly record and summary rules.

## Generation workflow
The export workflow follows these steps:
  1. The manager selects a month and year.
  2. PARKS validates the import and synchronization state for that period.
  3. PARKS prepares the corresponding `Export/{month}_{year}/` folder.
  4. PARKS creates the single combined manager summary PDF.
  5. PARKS creates one employee daily-entry PDF for every included employee.
  6. Existing files with the same export filenames are replaced.
  7. PARKS presents the generated summary and employee export status in the web application.
  8. The manager opens the summary PDF inside the web application.
  9. The manager confirms the summary report.
  10. Sending actions become available only after confirmation.

> The manager is not required to open every employee PDF before sending, but the manager can. The mandatory review applies to the combined summary PDF only.

## In-application review
- The generated summary PDF must be reviewable inside PARKS using an embedded PDF viewer.
- The review screen should provide:
  - The selected month and year.
  - The summary PDF embedded in the page.
  - A download option.
  - A clear confirmation action.
  - The current generation state.
  - The current sending state for managers and employees.

- Employee PDFs are generated and stored, but opening each employee PDF is not required for batch confirmation.

## Confirmation and invalidation
- Review and confirmation are mandatory before either category of report can be sent.
- The manager must review the summary PDF and explicitly confirm that the generated reports are ready for delivery. Confirmation applies to the generated export batch, not permanently to the month.

If the underlying synchronized data changes after generation, the existing generated files and confirmation become invalid. The system must then require:

1. Regeneration of the PDFs.
2. Review of the new summary PDF.
3. Confirmation of the new export batch.

Sending must remain disabled until these steps are complete. Regeneration also resets delivery states because the file contents may have changed.

## Separate sending actions
- The two delivery actions are independent:
  - **Send summary to managers**
  - **Send employee PDFs**

- The manager may send one category without automatically sending the other. Each action has its own progress and result state.
- The interface should show, for each action:
  - Number of successful deliveries.
  - Number of failed deliveries.
  - Pending deliveries.
  - Failure explanations.
  - Retry controls for failed deliveries.

A successful delivery must not be sent again when the manager retries failed deliveries. Regeneration creates a new export state and permits delivery of the new files after the new confirmation.

## Manager recipients
- The workspace has a configurable list of manager email addresses. The list can be changed as needed by an authorized manager or workspace owner.
- The list must support:
- Adding an address.
  - Removing an address.
  - Editing an address.
  - Email format validation.
  - Showing the configured recipients before sending.

The summary PDF is sent to every configured manager. Each manager should receive an individual email so that recipient addresses are not exposed to other managers.

The manager recipients receive only the one combined summary PDF. They do not receive the employee PDFs as part of the summary delivery.

## Employee recipients
- Each employee PDF is sent only to the email address stored on the matching employee record.
- Employee delivery rules are:
  - One employee report per email.
  - The matching employee is the only employee recipient.
  - Other employees must not be included in `To`, `CC`, or `BCC`.
  - The employee receives only their own daily-entry PDF.
  - The employee’s current email address must be revalidated before sending.

- The employee report delivery must remain separate from manager summary delivery.

## Delivery status and failure handling
Delivery status must be tracked independently for each recipient and report type. A conceptual export batch may contain states such as:

```text
Manager summary → manager-one@example.com → Sent
Manager summary → manager-two@example.com → Failed
Angelina report → angelina@example.com → Sent
Robert report → robert@example.com → Pending
```

The status should include enough information to support the manager’s next action:

- Pending.
- Sent.
- Failed.
- Failure reason.
- Sent timestamp.
- The export file associated with the delivery.

A successful delivery must remain successful when another recipient fails. Failed deliveries can be retried independently.

Sending failures must not cause already-sent reports to be resent. PDF generation failures must be reported per generated file and must prevent confirmation when the export batch is incomplete.

## Regeneration behavior
For the current version, regeneration replaces an existing PDF with the same filename in the selected month folder.

For example, a regenerated file replaces:

```text
Export/06_2026/Schicht_Angelina_Juni_2026_EXPORT.pdf
```

Replacing files is sufficient for the current workflow. Future audit versioning may preserve older files and mark them as superseded. A superseded file would remain available for audit history but would no longer be the current report and must not be sent again.

Regardless of whether replacement or future versioning is used, a changed PDF must be treated as a new export batch for confirmation and delivery purposes.

## Relationship to the legacy Apps Script

The legacy Apps Script contains separate concepts for PDF generation and PDF sending, including a `Final_pdf` folder and spreadsheet status columns. The web application moves this workflow into the backend and configured workspace Drive structure.

The current web application rules are:

- Use `Export`, not the legacy `Final_pdf`, as the export folder.
- Store PDFs in the selected month/year subfolder.
- Use synchronized Sheets preview data as the source.
- Track generation, confirmation, and delivery state in the application workflow rather than relying on spreadsheet status columns.
- Keep manager summary and employee delivery as separate actions.
- Use Gmail API authorization from the connected Google account.

The legacy Apps Script remains a reference for business and formatting behavior but is not the execution layer for the new workflow.

## Future extensions

The following are intentionally deferred:

- Audit versioning and superseded PDF history.
- A setting to omit calendar days without entries from employee PDFs.
- Alternative email providers.
- Configurable sender aliases.
- Scheduled automatic generation or sending.
- Automatic background detection of spreadsheet changes.
- Additional report formats or localized email templates.
