## Goals

- [] Let approved managers sign in with Google.
- Present employee data and common management actions in a simple interface.
- Read and update operational data stored in Google Sheets.
- Browse the configured PARKS folder and operate on Google Sheets inside it.
- Keep Google credentials and tokens on the server.
- Replace repetitive spreadsheet work with validated, auditable workflows.
- Remain extensible for other Google Workspace APIs.

## Initial non-goals

- Recreating every Google Drive or Sheets feature.
- Supporting arbitrary public Google accounts.
- Supporting multiple managers, manager assignment, ownership transfer, Gmail, sharing administration, version history, or Shared Drives.
- Migrating the existing Google Apps Script workflow in the initial Drive/Sheets foundation.
- Append semantics, spreadsheet formatting, file moves, trash, and deletion in the initial foundation.
- Adding background synchronization before interactive workflows are stable.

---
- Django application `workspace` --- coordinates both Google Drive folders and Google Sheets operations
- owns the PARKS folder, Drive authorization, and spreadsheet interactions
    