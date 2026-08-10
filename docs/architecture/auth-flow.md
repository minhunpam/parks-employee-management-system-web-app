# Authentication and Authorization Flow

- When user gets access `auth/google` endpoint, `google_login` is called

## What happens in `google_login`
- 

## `RefreshError`
- This exception is raised when the **stored Google OAuth refresh token is no longer valid**. Reaons for that could be:
- The user has revoked the Google account
- The Google account has expired
- Belongs ot a different OAuth client

### How to trigger this:
1. In the Google Account settings, click **Delete all connection/ Remove access** from your applicaton
2. Return to the app and trigger workspace validation or CSV import

### Effects to the app session:
- Removing access from Google does not automatically log the user out of your Django app. The app session remains active, but the stored Google refresh token fails when `build_services()` calls `credentials.refresh()`.
---
- App session: proves the user is logged into your application.
- Google connection: authorizes API access to Drive/Sheets.

Revoking Google access does not inherently invalidate the app session. Many applications keep the
session alive and request reconnection only when the integration is used.

