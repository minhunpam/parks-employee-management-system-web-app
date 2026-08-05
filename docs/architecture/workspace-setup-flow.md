- After being redirected to `workspace/setup` page, user will see a form to configure their workspace.
- This form will ask the user to enter:
  1. Drive root folder ID or UR
  2. Main spreadsheet ID or URL
- Once the user enters the required information, submitting the form triggers the event `submit`.

## `submit` Event
- It extracts the payload from the from and feed that payload to the `saveSetup()` function.

### `saveSetup()
- It makes POST request with request's body being the passed-in payload to the Django backend.
- [Backend handles the request](#how-django-backend-handles-the-request)
- Frontend receives the response, then handles and displays the result to the user accordingly.
  - For a successful setup, it will navigate the user to the entry page, in which the UI for main logic will be displayed.
    - **[See this documentation to understand more](/home/minhun/dev/parks/parks-employee-management-system-web-app/docs/architecture/main-logic-flow.md)**
---

## How Django backend handles the request
- The first thing the backend does is with the request's body is:
- [Parsing the resource IDs](#parsing-the-resource-ids)
- After that, we will try to fetch an existing workspace configuration attached to the request user:
  - If no existing configuration is found, we will create a new one.
  - If an existing configuration is found, but the root folder it and the spreadsheet id were changed, it will raise 400 Error and ask the user for confirmation to update the configuration ---> Restart `saveSetup()`
- Next step is [validating the resource IDs](#validating-the-resource-ids)
- After the validation, for non-existing configuration instance, a new one will be created and saved to the database (_at least the Django admin DB for now_). The spreadsheet will be inspected to determine if it contains the `Mitarbeiterdaten` sheet.
  - If exists, it will return a 200 response back to frontend
  - Otherwise, it will return a 422 response back to frontend


### Parsing the resource IDs:
- Removing any leading/trailing whitespace from the resource IDs.
- Depends on the resource type, either a folder or a spreadsheet, a matching ReGex pattern is used on a full url path
  - Example:
    1. Folder: `https://drive.google.com/drive/u/0/folders/<folder_id>`
    2. Spreadsheet: `https://docs.google.com/spreadsheets/d/<spreadsheet_id>/edit?gid=0#gid=0`

- However, if the user just gives the folder or spreadsheet ID, another handling step using `urlparse` is needed
- If the given value is an ID, it should be fine, but if it is an invalid URL, it should raise a `ValueError`.

- The final return value is: **folder or spreadsheet ID**

### Validating the resource IDs:
- Fetch the Google Connection of the user

#### Build Google Services
- Decrypt the refresh token stored within the Google Connection instance
- Create Google credentials and obtain a fresh access token via the decrypted refresh token
- Build the API clients for the Google Drive and Sheets

#### Validate the resources with the built Google APIs
- Google Drive API checks whehther:
  - The root folder exists
  - The folder has the correct permissions
  - The spreadsheet exists
  - The spreadsheet has the correct permissions

- Google Sheets API retrieves spreadsheet-specific information:
 - Spreadsheet title
 - Sheet/tab names
 - Spreadsheet structure
 ---
- Essentially, a Google Sheet file is managed by Google Drive, regardless of whether it was created:
  - In Google Drive
  - In the Google Sheets web app
  - From a template
  - Through the Sheets API

- However, Google Sheets has its own API for spreadsheet-specific data, such as:
  - Sheet tabs
  - Cells and values
  - Formatting
  - Formulas
  - Spreadsheet properties

 So:
 ```text
   Google Drive API → file location, ownership, sharing, permissions
   Google Sheets API → spreadsheet contents and structure
 ```