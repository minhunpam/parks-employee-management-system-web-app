# Workspace Setup Plan
This document captures the agreed plan for the workspace setup page at `src/frontend/workspace/setup.html`.

## Purpose
- The setup page is a hybrid setup/settings screen where an owner configures the Google Drive and Google Spreadsheet resources used by the workspace.
- It should support first-time configuration and later changes, but changes to foundational IDs must be handled carefully.

## Configuration
- The setup page configures two required resources:
  1. Google Drive root folder
  2. Main Google Spreadsheet

Both inputs should accept either:
  - raw ID
  - full Google Drive / Google Sheets URL
The parsed IDs are saved in the backend database via `WorkspaceConfiguration`.

- For now, the model should stay simple:
  ```python
  class WorkspaceConfiguration(models.Model):
      owner = models.OneToOneField(...)
      root_folder_id = models.CharField(max_length=255, unique=True)
      spreadsheet_id = models.CharField(max_length=255, blank=True)
      configured_at = models.DateTimeField(auto_now_add=True)
  ```

`root_folder_id` remains unique and required.

## Permission Model
- Use the current owner-per-user model.
- For now, “admin/owner only” means the logged-in user manages their own `WorkspaceConfiguration`. No multi-user workspace membership or admin roles are introduced yet.

## Google OAuth Scopes
- The app should use explicit scopes for both Drive and Sheets.
- Current Drive scope is not enough for reliable spreadsheet inspection and modification. Add:
  ```txt
  https://www.googleapis.com/auth/spreadsheets
  ```

- If a user has connected Google but is missing the Sheets scope, the setup page should show an explanation and a **Reconnect Google** button instead of auto-redirecting unexpectedly.

## Validation Requirements
- After submitting IDs, validation should run automatically.
- Validation should verify:

1. **Drive root folder**:
  - folder exists
  - current Google account/app has write access

2. **Main spreadsheet**:
  - spreadsheet exists
  - current Google account/app has write access
  - spreadsheet contains a `Mitarbeiterdaten` sheet
  - `Mitarbeiterdaten` headers match the canonical schema

### Required Drive subfolders
- The root folder should contain these top-level folders:
  - `Import`
  - `CSV Archiv`
  - `Final_csv`
  - `Final_pdf`

 > These names come from the legacy Apps Script reference in `src/frontend/apps_scripts/helper.js`.

## Saving and Readiness Model
- The setup state has two layers:

1. **Connection**:
  - Represents whether valid, writable Drive root and spreadsheet IDs are saved.
  - Possible display states:
    - not configured
    - configured

2. **Workspace**:
  - Represents whether the expected Drive/spreadsheet structure is ready.
  - Possible display states:
    - needs attention
    - ready

> The app should save valid IDs first, even if repairable issues remain. After saving, the page shows a repair checklist.

Example: if the Drive folder and spreadsheet are writable but `Import` is missing, save the IDs and show a **Create missing folders** action.

## Repair Actions
- The setup page should offer repair actions for known issues.

### Missing Drive folders
- If any required top-level folders are missing, show one button:
  ```txt
  Create missing folders
  ```

- This creates all missing required folders at once.

### Missing `Mitarbeiterdaten` sheet
- If the spreadsheet does not contain `Mitarbeiterdaten`, show a button to create it.
- When created, it should use the canonical headers below.

### Header mismatch
- If `Mitarbeiterdaten` exists but headers differ, show the differences and offer a **Fix headers** action.
- **Fixing headers should preserve existing data by mapping/reordering columns into the canonical order. It should not blindly overwrite row 1 while leaving data under the wrong columns.**
- Header matching should use known aliases, not fuzzy matching.

## Canonical `Mitarbeiterdaten` Schema
The canonical headers are:
  ```txt
  Vorname
  E-Mail
  Arbeitstage/Woche
  Resturlaub Vorjahr
  Urlaub aktuelles Jahr
  Sollstunden Monat
  ```

This intentionally follows the current employee creation script behavior from `src/frontend/apps_scripts/mitarbeiterverwaltung.js`.

## Confirmation for Changes
- If an existing saved Drive root folder ID or spreadsheet ID is changed, the app should:
  1. parse the new input
  2. verify the new resource exists and is writable
  3. then require typed confirmation before saving

- Typed confirmation phrase:
  ```txt
  CHANGE WORKSPACE CONFIG
  ```

The user may update only one ID at a time. Unchanged saved values remain unchanged.

## User Experience

- The setup page should display saved resources as:
  - human-readable name
  - open link
  - ID available/copyable in details
- After first-time setup, the user should stay on the setup page. They may want to interact with the newly configured Drive folder immediately.
- After later changes, the user also stays on the page and sees a success message.
- Every repair action should automatically re-run validation afterward.
- The page should also include a manual button:
  ```txt
  Re-run setup check
  ```
- This is useful if the manager manually creates folders/sheets in another tab.
- Permission/access errors should be actionable, not overly technical. They should explain likely causes such as:
  - wrong ID/URL
  - resource not shared with the connected Google account
  - insufficient write permission

## Workflow Hint
- After setup, the page should include a short “What to do next” hint for the manager.
- The expected monthly workflow is:
  1. Put monthly CSV files into the `Import` folder.
  2. Use the web app monthly import workflow to process them.
  3. Review generated spreadsheet/report data.
  4. Export/send PDFs later.
- CSV import processing should not live on the setup page. It should be implemented on a separate monthly import page.
- When workspace status is ready, show a primary CTA:
  ```txt
  Go to monthly import
  ```

- Target path:
  ```txt
  /workspace/import
  ```

## Implementation Shape
- Follow the existing project pattern:
  - Django backend
  - Django-rendered HTML templates
  - JavaScript `fetch` calls for setup actions
- Do not convert this into a separate SPA framework.
- Use JSON endpoints under the existing `workspace` URL namespace.

- Possible endpoint shape:
  ```txt
  /workspace/setup/api/save/
  /workspace/setup/api/check/
  /workspace/setup/api/repair/folders/
  /workspace/setup/api/repair/mitarbeiterdaten/
  /workspace/setup/api/repair/headers/
  ```

The exact endpoint names can be adjusted during implementation, but they should remain under `workspace`.

## Legacy Apps Script Context

The folder `src/frontend/apps_scripts/` contains legacy/reference Google Apps Script logic. The long-term direction is to centralize spreadsheet processing in the web app/backend instead of requiring each spreadsheet to have attached Apps Scripts.

Important legacy folder constants:

```js
const FINAL_CSV_FOLDER_NAME = "Final_csv";
const IMPORT_FOLDER_NAME = "Import";
const CSV_ARCHIV_FOLDER_NAME = "CSV Archiv";
const FINAL_PDF_FOLDER_NAME = "Final_pdf";
```

The setup page should validate this folder structure, but processing logic should gradually move into the backend.
