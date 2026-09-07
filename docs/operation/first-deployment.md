# First deployment

This document describes the agreed direction for bringing the PARKS Employee Management System to its first real users.

## Implementation status

The repository has the core application and local container packaging in place, but the first production deployment has not been completed. The remaining work is operational: provision and harden the VPS, configure production secrets and Google resources, set up DNS and HTTPS, establish encrypted off-site backups and monitoring, and document and test the deployment and recovery procedures. GitHub Actions currently validates changes; it does not deploy them.

## Deployment goals

The first deployment should:

- keep monthly infrastructure costs close to €10
- support one restaurant and approximately 5–20 users
- keep development and production clearly separated
- be maintainable by a developer who can follow documented Linux procedures
- provide a safe path to future scaling
- protect employee and Google connection data

The application will remain a single Django application with Django-rendered templates and JavaScript interactions. It will not be split into separate frontend and backend services for the first deployment.

## Production architecture

**Status: NOT DONE.** The application-side packaging is implemented, but no production VPS or running production stack has been verified.

The shared Docker Compose definition already provides Django/Gunicorn, PostgreSQL, Nginx, persistent volumes, and a database health check. The production override adds restart policies and a production environment file, but it currently exposes HTTP only. Hetzner provisioning, Ubuntu setup, SSH-key-only access, firewall hardening, HTTPS, and off-site database storage remain outstanding.

The initial production architecture is:

```text
Browser
  ↓ HTTPS
Nginx
  ↓
Gunicorn + Django
  ↓
PostgreSQL
```

All application services will initially run on one EU-based Hetzner VPS. PostgreSQL will run on the same server in the first release to minimize cost. The database will use persistent storage and will be backed up to storage separate from the VPS.

Docker Compose is the recommended packaging and runtime approach. It makes the application, database, and supporting configuration reproducible and provides a path to move services to separate infrastructure later.

The server should use Ubuntu LTS and SSH key authentication. Password-based SSH access should not be used.

## Development and production separation

**Status: PARTIALLY DONE.** Development and production use separate Compose overrides, environment files, and database modes. The single environment-driven Django settings module enables production security settings when `DJANGO_DEBUG=False`, and `.env` plus credential files are excluded from Git. Separate production database contents, production Google resources, production credentials, and a verified production environment have not yet been created.

Development and production use the same application codebase. They are separated through branches, data, credentials, and environment configuration.

### Development

Development uses:

- local Django execution
- local test data
- local environment variables
- development Google OAuth credentials and resources
- feature branches

### Production

Production uses:

- a separate production database
- production environment variables
- production Google OAuth credentials
- production Google Drive and Sheets resources
- HTTPS and the production domain

The development database must not be copied directly into production. The first production database should be created empty and populated with intentionally selected real data through the application’s normal workflows.

Configuration should be controlled by environment variables using one consistent settings structure. Production secrets must never be committed to Git.

## Domain and DNS

**Status: NOT DONE (intentionally deferred).** The target subdomain is agreed, but DNS access is unavailable and there is no production server IP yet. The `A` record, production-domain routing, and Let’s Encrypt certificate still need to be configured after VPS provisioning.

The existing domain is:

```text
https://www.parks-graz.at/
```

The application should use the separate subdomain:

```text
https://app.parks-graz.at
```

This will not replace or modify the existing restaurant website.

DNS access is currently not available to the developer, so this step is intentionally deferred until the production server has been created and has a public IP address.

At that point, whoever manages DNS for `parks-graz.at` must add an `A` record similar to:

```text
Type: A
Name: app
Value: <production server IP>
TTL: 3600
```

HTTPS should then be configured with a Let’s Encrypt certificate.

## Google OAuth and user access

**Status: APPLICATION DONE; PRODUCTION SETUP NOT DONE.** Google sign-in, inactive-user approval flow, approved-user access, Drive/Sheets/Gmail scopes, and Fernet-based refresh-token encryption are implemented and covered by application code/tests. A dedicated production Google Cloud project, production OAuth credentials/resources, publication, and Google verification for personal Gmail access have not been completed.

The application will support a mixture of company Google Workspace accounts and personal Gmail accounts.

The intended access policy is:

1. Anyone may attempt to sign in with Google.
2. The application creates or identifies the user.
3. Unapproved users remain on the approval-pending page.
4. An administrator approves eligible managers.
5. Only approved managers can enter the application.

Employees do not log into the web application initially. They receive generated PDFs by email.

Production OAuth credentials should be stored in a dedicated production Google Cloud project rather than the development project. Because personal Gmail accounts are supported, the OAuth application should eventually be published and submitted for Google verification. Keeping it in testing mode is suitable only for development or limited initial testing.

The application requests Google permissions for the services it uses, including Drive, Sheets, and Gmail sending. Refresh tokens must remain encrypted, and the production Fernet key must be stored as a deployment secret.

## Administration

**Status: APPLICATION DONE; OPERATIONAL HARDENING NOT DONE.** Django admin can approve users by changing `is_active`, and the initial administrator can be created with Django’s normal administration workflow. A production superuser has not been created, and independent protection of the admin endpoint still needs to be configured and verified.

Initially, user approval will be handled through the Django admin panel. The developer will be the initial administrator. Access to the Django admin must be protected independently from normal application access.

A dedicated in-application approval page may be considered in a later release if approval becomes a regular operational responsibility for restaurant managers.

## Email sending

**Status: DONE FOR THE FIRST RELEASE.** The application sends generated PDFs synchronously through the logged-in manager’s connected Gmail account, using the Gmail API scope already configured in the application. No separate sender account or transactional provider has been added, consistently with the agreed first-release decision.

Generated employee and manager PDFs will initially be sent through the currently logged-in manager’s connected Google account.

This avoids introducing an additional email service or account. The sender may therefore differ depending on which manager performs the operation.

A dedicated company Google account or transactional email provider can be considered later if a stable sender identity, centralized delivery history, or improved delivery monitoring becomes necessary.

## Git workflow

**Status: PARTIALLY DONE.** The repository has `dev`, `staging`, and `main` branches, and the CI workflow runs pull-request checks for `dev`/`main` plus checks on `staging`. The workflow includes backend tests, frontend tests, Ruff, Django deployment checks, and CSS build verification. GitHub repository privacy, `main` branch protection, required checks, and the actual pull-request approval policy still need to be configured and verified.

The repository should remain private on GitHub.

The standard workflow is:

```text
feature branch
    ↓
Pull request
    ↓
Automated checks
    ↓
Merge into protected main
    ↓
Production deployment approval
    ↓
Deployment to VPS
```

The `main` branch should be protected so that production code cannot be changed through direct pushes. Pull requests and passing automated checks should be required before merging.

GitHub Actions should run at least:

- backend tests
- frontend tests
- Ruff or equivalent lint checks
- Django deployment checks
- production CSS build validation

For a solo developer, a separate reviewer is not initially required, but the pull-request and automated-check workflow should still be followed.

## GitHub Actions and deployment

**Status: NOT DONE.** GitHub Actions currently performs validation only. There is no deployment workflow, no configured development/production GitHub environments or deployment secrets, no manual production approval gate, and no documented image tagging/retention or rollback implementation. The initial deployment and subsequent automated deployment process remain to be established.

GitHub Actions should use separate environments and secrets for development and production.

Production deployment should require a manual approval after the automated checks pass. This separates validating a code change from intentionally releasing it to users.

The first production deployment may be performed manually while the server and deployment process are being verified. Subsequent deployments should use GitHub Actions and the same documented process every time.

A deployment should normally happen during a quiet maintenance window. A brief interruption while the Docker services restart is acceptable for the first release. Zero-downtime deployment is not required initially.

Docker images should be associated with a commit or release identifier. The previous production image should remain available so that a bad application release can be rolled back quickly.

## Database migrations

**Status: PARTIALLY DONE.** Django migration files exist and the CI workflow runs the test suite and deployment checks. No production database has been created, and the backup-before-migration/deploy sequence has not yet been executed or documented as an operational procedure.

The initial deployment may use a straightforward migration process after the production environment has been verified.

For later releases, the preferred safer sequence is:

```text
create backup
    ↓
run database migrations
    ↓
deploy the new application version
```

Migrations must be reviewed carefully because application data is shared by the production users. The deployment process should preserve the ability to return to the previous application image when possible.

## Backups and recovery

**Status: NOT DONE.** There is no implemented daily encrypted PostgreSQL backup, off-site object-storage destination, 30-day retention policy, restoration test, or replacement-VPS rebuild procedure. This is a production blocker because the database currently has no verified disaster-recovery path.

The production PostgreSQL database should be backed up daily.

Backups must be encrypted and stored off-site, meaning separately from the production VPS. A separate EU-based object-storage service is preferred. A backup stored only on the same VPS does not provide adequate protection against total server loss.

The initial policy is:

- one automated backup per day
- 30-day retention
- off-site storage
- encrypted backup contents
- periodic restoration testing, targeted quarterly

Backups protect application data such as users, workspace configurations, employee records, and processing history. Google Drive files and Google Sheets are external resources and are not automatically included in the PostgreSQL backup policy. Their backup strategy can be designed separately.

The disaster-recovery process should include a documented rebuild procedure for creating a replacement VPS, restoring the database, configuring secrets, and starting the application. The procedure should be tested periodically rather than being attempted for the first time during an incident.

## Monitoring and maintenance

**Status: NOT DONE.** No public uptime check, server/application log collection, error notification route, or operating-system security-update procedure has been configured. These need to be established before production use.

The first release should use basic monitoring:

- an uptime check for the public application
- server and application logs
- error notifications sent to the developer

A full metrics and observability platform is not required initially. Monitoring should be improved if usage, background processing, or operational complexity increases.

The server should receive automatic operating-system security updates. Larger operating-system upgrades and dependency upgrades should be performed manually during a maintenance window.

## Application processing model

**Status: DONE FOR THE FIRST RELEASE.** CSV imports, Google API operations, PDF generation, and email delivery run synchronously in the Django request flow, and no Redis or worker service is included in the Compose stack. This matches the agreed inexpensive first-release architecture; background jobs remain a later optimization.

CSV imports, Google API operations, PDF generation, and email delivery will run synchronously during the first release. This keeps the architecture inexpensive and avoids adding Redis or a worker service.

Users may need to wait while a large operation completes. Long-running work should be moved to background jobs in a later release when performance or user experience requires it.

## Access and privacy baseline

**Status: PARTIALLY DONE.** The application restricts access to approved users, uses CSRF protection, enables production cookie/SSL/HSTS settings, and encrypts stored Google refresh tokens. Production deployment controls, log/backup privacy verification, and a formal historical-data retention/deletion policy are not yet in place.

The initial production system is intended for one restaurant. Only approved managers can access the web application. Employee data should not be exposed through public endpoints, logs, GitHub, backups, or development environments.

Historical employee data will be retained indefinitely for now to preserve reporting and business history. A formal retention and deletion policy should be reviewed in a later release, especially with regard to employee privacy obligations.

## Cost and scalability

**Status: DESIGN DONE; COST NOT YET VERIFIED.** The low-cost architecture is designed around one VPS, colocated PostgreSQL, object storage, and GitHub Actions, with documented future scaling options. No VPS, object-storage account, monitoring setup, or production bill exists yet, so the approximately €10/month target has not been demonstrated.

The initial infrastructure target is approximately €10 per month. This is achieved by using:

- one small Hetzner VPS
- PostgreSQL on the same VPS
- no permanent staging server
- inexpensive off-site object storage
- basic monitoring
- GitHub Actions for automation

This architecture is sufficient for one restaurant and the expected initial user count. Future scaling options include:

- moving PostgreSQL to managed infrastructure
- moving the Django application to a managed platform
- adding a background worker and queue
- introducing a permanent staging environment
- adding zero-downtime deployments
- adding richer monitoring and alerting

These changes should be made when actual usage or reliability requirements justify their additional cost and complexity.

## Deferred items

The following items are intentionally not part of the first deployment:

- DNS configuration, until the production server IP exists
- permanent staging infrastructure
- background job processing
- zero-downtime deployment
- a dedicated email-sending account or transactional email provider
- in-application user approval management
- continuous or hourly backups
- full observability infrastructure
- formal historical employee-data deletion policy
