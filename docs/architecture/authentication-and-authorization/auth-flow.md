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

## Approval pending
- The associated endpoint is not coupled with the demand of loggin the user in
- since if an unauthenticated and inactive user deliberately enters this page, it would require them to log themselves in
  - This would more complexity, since "why do we need to add a new authenticated user to the database, just because they want to see the `approval-pending` page?"
  - And we can just instead redirect them back to home
- Also the reason for `@login_required` here is:
  - An inactive user cannot reach the `login()` call ---> he is also an unauthenticated user === anonymous user
  - He is redirected to approval pending page, but since the page is guarded by `@login_required` which rejects anonymous user ---> asks him to login
  - Eventually we are stuck in a login-loop

### Rules
- **Authenticated User** ---> workspace entry page
- **Authenticated Inactive User** ---> approval pending page waiting until the admin approves
- **Unauthenticated User/Anonymous User** ---> redirect to home

## Logout
- Use a CSRF-protected POST request
- Call Django’s logout(request), clearing the entire session.
- Clear pending approval and OAuth state.
- Preserve the stored Google connection.
- Redirect to the public home page.
- Leave protected pages guarded by @login_required.