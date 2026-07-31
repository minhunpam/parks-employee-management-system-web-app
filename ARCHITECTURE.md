# PARKS Employee Management System Architecture

## Project overview

This project is an employee management system for the PARKS restaurant. It provides a focused interface over Google Workspace so managers do not have to edit spreadsheets manually or run separate container-bound Google Apps Script functions for individual tasks.

The first release authenticates one manager with Google and provides a focused workspace over one PARKS root folder shared from that manager's My Drive. The first Google Workspace operations are intentionally small: create a Google Sheets spreadsheet in that folder, read a cell range, and replace the values in a cell range. Existing Google Apps Script business workflows will be migrated later.

## Current implementation status

The repository currently implements only the identity foundation:

- A custom email-based Django `User`.
- A one-to-one `GoogleConnection` keyed by Google's stable `sub` identifier.
- Google authorization-code login with OAuth state validation and PKCE.
- Creation of new users as inactive until manually approved.
- An approval-pending page for inactive users.
- A Django session for active users.

The current login flow requests only `openid`, email, and profile scopes. It uses online access, does not retain usable Drive credentials, and redirects an active user to `https://www.google.com/` as a temporary placeholder.

The following agreed components are not implemented yet:

- A separate Drive authorization flow with offline access.
- Secure refresh-token encryption and persistence.
- The Drive entry, connection, setup, and workspace pages.
- Root-folder configuration and permanent workspace ownership.
- Drive and Sheets service modules.
- Google Sheets create, range-read, and range-write operations.

Sections below describe the agreed target for the first release unless explicitly marked as current behavior.

## Technology stack

### Frontend

- HTML5
- Django templates
- Tailwind CSS
- Small amounts of JavaScript for dialogs, uploads, and dynamic file actions

### Backend

- Python and Django
- Django authentication, sessions, CSRF protection, and permissions
- `google-auth` and `google-auth-oauthlib` for OAuth 2.0
- `google-api-python-client` for Drive and Sheets
- Gunicorn or another production WSGI/ASGI server

### Storage

- Google Sheets for restaurant and employee operational data
- Google Drive for files and folders
- **PostgreSQL** for Django users, sessions, permissions, audit records, and encrypted Google refresh tokens
- **SQLite** may be used for local development

- Google Sheets is an operational data source, not a safe replacement for Django's security database. 
- OAuth tokens, sessions, application permissions, and audit records must not be stored in a spreadsheet.

## High-level architecture

```text
┌──────────────────────────────────────┐
│ Browser                              │
│ Django templates + Tailwind + JS     │
└──────────────────┬───────────────────┘
                   │ HTTPS
                   │ Django session + CSRF token
                   ▼
┌──────────────────────────────────────┐
│ Django application                   │
│                                      │
│ Authentication and authorization     │
│ Employee management workflows        │
│ Drive and Sheets service layer       │
│ Validation, permissions, and audit   │
└───────────┬──────────────┬───────────┘
            │              │
            ▼              ▼
┌───────────────────┐  ┌──────────────────────────┐
│ PostgreSQL        │  │ Google Workspace APIs    │
│ Users/sessions    │  │ Drive                    │
│ Encrypted tokens  │  │ Sheets                   │
│ Roles/audit       │  │ Gmail in a later phase   │
└───────────────────┘  └──────────────────────────┘
```

The browser communicates with Django for normal operations. Django refreshes Google access tokens and calls Google APIs for the signed-in user. Client secrets and refresh tokens are never exposed to browser JavaScript.

## Django application boundaries

```text
src/backend/
├── config/                  # Settings, root URLs, WSGI/ASGI
├── accounts/                # Google login and application users
├── employees/               # Employee domain and workflows
├── workspace/
│   ├── credentials.py       # Credential construction and refresh
│   ├── drive_service.py     # Drive integration
│   └── sheets_service.py    # Sheets integration
├── audit/                   # Important-action audit records
├── templates/
├── static/
└── manage.py
```

- Google API calls should remain in service modules rather than Django views.

## Authentication and authorization

Use the OAuth 2.0 authorization-code flow for a web-server application:

```text
User selects "Continue with Google"
        ↓
Django creates and stores a random OAuth state value
        ↓
Browser is redirected to Google
        ↓
Google authenticates the user and requests consent
        ↓
Google redirects to Django with an authorization code
        ↓
Django validates state and exchanges the code
        ↓
Django validates the Google identity
        ↓
Django creates or updates the local user and connection
        ↓
Django starts a server-side application session
```

Suggested routes:

```text
GET  /auth/google/
GET  /auth/google/callback/
POST /auth/logout/
POST /auth/google/disconnect/
```

Request offline access during initial connection so Google can issue a refresh token. Do not force consent on every login; use it only for initial connection or recovery from a revoked connection.

### Application roles

- `viewer`: can view employee data and permitted files.
- `manager`: can change employee data and manage permitted files.
- `administrator`: can manage approved users, connections, and configuration.

Permissions must be enforced in Django views and services. Hiding a frontend button is not an authorization check.

## OAuth scopes

Authentication begins with:

```text
openid
email
profile
```

For a limited Drive MVP, prefer:

```text
https://www.googleapis.com/auth/drive.file
```

`drive.file` lets the app work with files a user explicitly opens, shares with the app, or creates through it. It can be combined with Google Picker.

A complete interface over every file requires a broader scope such as `drive.readonly` or `drive`. These are restricted scopes and add Google verification and possible security-assessment requirements. Do not request them unless full-Drive access is mandatory.

The Sheets scope should match the feature: use read-only access if the app only displays data and request write access only for editing. Prefer known restaurant spreadsheet IDs over unrestricted Drive discovery.

## Data ownership

### Google Sheets

Sheets contains operational records such as employee information and schedules. Each structured sheet needs:

- A stable spreadsheet ID configured outside source code.
- A documented tab and column schema.
- A stable employee ID that does not depend on row number.
- Validation before values are written.
- Handling for missing, renamed, or malformed tabs.
- Concurrency handling to prevent silent overwrites.

Views and templates should not know spreadsheet ranges or column positions.

### Django Models/ Databases

```text
User <------ custom User
- id
- email
- display name
- active status
- application role

GoogleConnection
- user
- Google subject identifier
- encrypted refresh token
- granted scopes
- connected and updated timestamps

AuditEvent
- actor
- action
- target type and identifier
- non-sensitive change summary
- timestamp
```

- Access tokens are short-lived and normally need no permanent storage. 
- Refresh tokens must be encrypted with a key kept separately from the database.

## Google Drive integration

The Drive service layer should provide:

```python
build_drive_service(user)
list_files(user, folder_id=None, page_token=None)
get_file(user, file_id)
create_folder(user, name, parent_id=None)
upload_file(user, uploaded_file, parent_id=None)
rename_file(user, file_id, new_name)
move_file(user, file_id, destination_id)
trash_file(user, file_id)
download_or_export_file(user, file_id)
```

Suggested endpoints:

```text
GET    /drive/
GET    /drive/folders/<file_id>/
GET    /api/drive/files/
POST   /api/drive/folders/
POST   /api/drive/uploads/
PATCH  /api/drive/files/<file_id>/
DELETE /api/drive/files/<file_id>/
GET    /api/drive/files/<file_id>/download/
```

All endpoints require an authenticated, approved user. Mutating requests require CSRF protection and the appropriate permission. File listing must paginate and request only fields the UI needs. Google-native documents require export operations; uploaded binary files use download operations. Large transfers should be streamed or resumable.

## Frontend plan

```text
/                         Landing page and Google sign-in
/employees/               Employee list
/employees/<id>/          Employee details
/drive/                   Drive file browser
/drive/folders/<id>/      Folder contents
/settings/                Account and Google connection
/admin/                   Django administration
```

Reusable components include employee tables and forms, folder breadcrumbs, a file table or grid, search and sorting, upload progress, action menus, confirmation dialogs, and loading, empty, and error states.

Server-rendered templates are the default. Add JavaScript only where it materially improves the workflow.

## Error handling

The application must handle:

- Cancelled login or consent.
- Denied or partially granted scopes.
- Missing, expired, or revoked refresh tokens.
- Authenticated but unapproved accounts.
- Google API quota limits and temporary errors.
- Missing files, spreadsheets, or tabs.
- Insufficient Google or application permissions.
- Concurrent spreadsheet changes.
- Invalid uploads and excessive file sizes.

Errors should explain recovery without exposing tokens, private Google responses, or stack traces. Retry only idempotent operations automatically, using bounded exponential backoff.

## Security requirements

- Use HTTPS for every production request.
- Keep Django and Google secrets, database credentials, spreadsheet IDs, and encryption keys in environment variables or a secret manager.
- Never commit `credentials.json`, refresh tokens, or production configuration.
- Validate OAuth `state` before exchanging an authorization code.
- Use secure, HTTP-only, SameSite session cookies.
- Rotate the Django session after login.
- Enable CSRF protection for all state-changing requests.
- Encrypt refresh tokens at rest.
- Never log OAuth codes or tokens.
- Validate file IDs, spreadsheet values, uploads, and actions on the server.
- Apply role checks before Google API operations.
- Rate-limit authentication and expensive API endpoints.
- Audit material employee-data changes without copying unnecessary personal data into logs.
- Provide disconnect, token revocation, account deletion, and retention flows.
- Run `python manage.py check --deploy` against production settings.

Production settings must include `DEBUG = False`, correct `ALLOWED_HOSTS` and trusted CSRF origins, HTTPS redirection, secure cookies, and HSTS after HTTPS is confirmed.

## Testing strategy

### Unit tests

- OAuth state validation
- Approved-user and role checks
- Token encryption and credential refresh
- Sheet row-to-domain-object mapping
- Spreadsheet validation and updates
- Drive query construction and response mapping

Google API clients should be mocked in unit tests.

### Integration and end-to-end tests

- Successful, cancelled, and denied login
- New, returning, and unapproved users
- Revoked Google connections
- Employee reads and updates against a test spreadsheet
- Empty and paginated Drive folders
- Upload, create folder, rename, move, trash, download, and export
- Viewer denied a manager-only operation
- Google API errors and rate limits

Use a separate Google Cloud project, test accounts, test folder, and test spreadsheet. Automated tests must never modify production restaurant data.

## Delivery plan

### Phase 1: Foundation

- Confirm employee workflows and spreadsheet schema.
- Create the Django project and custom user model.
- Configure PostgreSQL and environment-based settings.
- Add base templates and Tailwind CSS.
- Separate development, test, and production settings.

### Phase 2: Identity and access

- Configure a development Google Cloud project and consent screen.
- Implement the authorization-code flow.
- Restrict access to approved users.
- Store encrypted refresh tokens.
- Implement logout, disconnect, and revoked-token handling.
- Add viewer, manager, and administrator roles.

### Phase 3: Read-only employee MVP

- Implement the Sheets service.
- Document and validate the spreadsheet schema.
- Display employee list and detail pages.
- Handle unavailable or malformed data cleanly.

### Phase 4: Employee editing

- Add validated create and update operations.
- Archive records instead of deleting rows destructively.
- Add confirmation, permission, concurrency, and audit behavior.

### Phase 5: Drive MVP

- Start with `drive.file` and Google Picker where possible.
- Add paginated file and folder listing.
- Add folder creation, upload, preview, download, and export.
- Add rename, move, and trash only when required.

### Phase 6: Production readiness

- Complete security, privacy, and retention reviews.
- Add rate limiting, monitoring, structured logging, and backups.
- Run unit, integration, end-to-end, and deployment checks.
- Deploy behind HTTPS with production settings.
- Complete Google verification required by the selected scopes.

### Phase 7: Later integrations

- Evaluate Gmail workflows and request Gmail scopes only when needed.
- Add background jobs if synchronization or notifications are needed.
- Add Shared Drive support if PARKS uses it.
- Revisit broader Drive scopes only if the per-file model is insufficient.

## Key architectural decisions

1. Django is the trusted backend and security boundary.
2. The browser receives a Django session, not persistent Google tokens.
3. Sheets stores operational data; PostgreSQL stores security and metadata.
4. Google API calls are isolated behind service modules.
5. Application authorization is separate from Google login.
6. OAuth scopes are minimal and introduced incrementally.
7. The initial interface is server-rendered and selectively enhanced with JavaScript.
8. Production and automated tests use separate Google resources.

## Open decisions

- Will access use one Workspace domain or an explicit account allowlist?
- Which employee fields and tabs form the canonical spreadsheet schema?
- Does the first release edit employee data or only display it?
- Will managers authorize with their own accounts, or will centrally owned restaurant resources use a dedicated Workspace setup?
- Is `drive.file` sufficient, or is a complete Drive browser mandatory?
- Which actions require immutable audit records?
- What are the retention and deletion rules for employee information?
