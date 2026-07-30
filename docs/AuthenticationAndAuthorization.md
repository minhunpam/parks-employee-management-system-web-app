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

### `User` and `GoogleConnection`
- `GoogleConnection` represents the link between a Django user and their Google account
- A `User` can exist without `GoogleConnection`
- The relationship is:
```
User                 GoogeConnection
 1  ----------------- 0 or 1
```
  - Every `GoogleConnection` must belong to exactly one `User`
  - A `User` may have zero or one `GoogleConection`

> For this application, most normal users will eventually have a connection. But keeping the models separate allows the application account and Google integration to have independent lifecycles