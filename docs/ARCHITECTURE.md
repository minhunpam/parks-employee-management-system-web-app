## Current flow
### Accounts
- At the moment, there is no dedicated landing page for this web page, I assume user would get directly into the `/auth/google/` page where they are asked to authenticate with their Google account.
- The user is then redirected to the `auth/google/callback`. In this view, a server-to-server authorization code exchange is performed.
  - Eventually, Google responds with an tokens: access token, refresh token and id token
  - However, for this phase, only id token is used for authentication
- Inactive user is then redirected into the `approval-pending` page. Otherwise, the user is redirected to the the entry point of the workspace

### Workspace
- A user without a google connection is redirected to `workspace/connect/` endpoint to initiate a `GoogleConnection` instace with:
  - encrypted refresh token
  - granted scopes
- A user with a google connection but without a workspace configuration that includes a valid Drive root folder id is redirected to `workspace/setup` endpoint to initiate a workspace configuration.