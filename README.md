# PARKS Employee Management System

A full-stack employee management platform that gives restaurant managers a focused interface for employee administration, working-time tracking, and monthly reporting without requiring them to manage Google Workspace manually.

> **Portfolio project:** This project was designed and implemented to solve a real operational workflow involving employee records, monthly CSV data, Google Drive, and Google Sheets.

## Why this project exists

The original workflow depended on manually managing Drive folders, importing employee CSV files, editing spreadsheets, and preparing reports. This application brings those steps into one guided workflow while preserving Google Sheets as the operational source for timesheet data.

## Key capabilities

- **Secure authentication:** Google OAuth 2.0 login with approval-based access control.
- **Workspace setup:** Connects a user to a Google Drive root folder and spreadsheet through a guided configuration flow.
- **Monthly CSV importing:** Detects the correct import folder, validates file names and content, imports employee records, creates missing spreadsheet tabs, and archives processed files.
- **Spreadsheet integration:** Reads employee sheets, calculates summaries, supports controlled manual entries, and synchronizes changes with the local database.
- **Employee management:** Handles employee registration, active and archived employees, working agreements, target hours, and employment dates.
- **Working-time and absence rules:** Calculates working time, breaks, public-holiday work, paid absences, vacation entitlements, and schedule-change balances.
- **Reporting:** Generates employee and manager PDF reports and supports email delivery through Gmail.
- **Operational resilience:** Revalidates external resources before mutations and reports authentication, permission, validation, spreadsheet, and archival failures separately.

## Technology

| Area | Technologies |
| --- | --- |
| Backend | Python, Django, Django ORM |
| Frontend | JavaScript, HTML templates, Tailwind CSS |
| Data | PostgreSQL in deployment, SQLite for lightweight local development |
| Integrations | Google OAuth 2.0, Google Drive API, Google Sheets API, Gmail API |
| Testing | Django test suite, Jest, jsdom |
| Deployment | Docker, Docker Compose, Gunicorn, Nginx |
| Code quality | Ruff and pre-commit hooks |

## Architecture

The application is organized into focused Django modules:

- `accounts` — users, Google authentication, and encrypted Google connections
- `workspace` — workspace configuration, Drive/Sheets/Gmail clients, CSV import, PDF export, and reporting
- `employees` — employee records, monthly/yearly summaries, working agreements, and vacation calculations
- `frontend` — server-rendered templates, Tailwind styles, and modular JavaScript behavior

External Google resources are accessed through dedicated client modules rather than being handled directly by page views. This keeps integration code isolated, makes workflows easier to test, and provides a clear boundary for error handling.

## Engineering highlights

### Validation-first integrations

Before importing or updating data, the application verifies the user's connection, workspace configuration, Drive folder, spreadsheet, file naming convention, CSV contents, and target month. This prevents stale or malformed external data from silently corrupting records.

### Business rules in the domain model

Employee and time-tracking rules are implemented as explicit domain logic rather than being left to the user interface. This includes working-day schedules, weekly and monthly target hours, public holidays, paid absences, vacation balances, and historical schedule changes.

### Safe external mutations

The import workflow revalidates its context before processing files, performs spreadsheet updates through a dedicated client, and archives files only after successful processing. Failures are surfaced with actionable status information so managers can recover from them.

### Automated testing

Backend tests cover employee registration baselines, working agreements, vacation entitlements, schedule recalculation, and migration behavior. Frontend tests cover shared behavior, authentication interactions, employee table behavior, and employee-detail state management.

## Running locally

### Prerequisites

- Python 3.12+
- Node.js and npm
- Docker and Docker Compose
- Google OAuth credentials with the required Drive, Sheets, and Gmail scopes

### Configuration

Copy the example environment file and provide the required local values:

```bash
cp .env.example .env
```

At minimum, configure the Django secret, Fernet encryption key, Google OAuth credentials, and PostgreSQL password. OAuth redirect URIs must match the credentials configured in Google Cloud.

### Start the application with Docker

From the repository root:

```bash
docker compose \
  --env-file .env \
  -f src/compose.yaml \
  -f src/compose.dev.yaml \
  -p parks-dev \
  up -d --build
```

The development application is available at `http://localhost:8000`.

### Run backend tests

```bash
cd src/backend
python manage.py test
```

### Run frontend tests

```bash
cd src/frontend
npm install
npm test
```

## Production-oriented deployment

The repository includes separate Docker Compose overlays for development and production. The production configuration uses PostgreSQL, Gunicorn, Nginx, HTTPS-related Django security settings, static-file serving, health checks, and restart policies.

## Project status

The core employee-management, workspace setup, Google integration, monthly import, spreadsheet preview/editing, reporting, and testing workflows are implemented. The project continues to evolve as business rules and operational requirements are refined.
