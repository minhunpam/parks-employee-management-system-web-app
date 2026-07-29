# Authentication and Authorization

## OpenID Connect and OAuth 2.0:

This project has 2 different questions to answer:
- OpenID Connect: Who is this person (**end-user**)?
- OAuth 2.0: What may the application (**client**) do for them

### OpenID Connect handles login
- When requesting: `openid, email, profile`
- Google returns an ID Token containing verified identity claims
- Django verifies that token and uses it to identiy the Google account

### OAuth2.0 handles Drive access
- Later, when you request: `https:://www.googleapis.com/auth/drive.file`
- Google can issue: an access token and a refresh token
- It is sent to the Drive API

