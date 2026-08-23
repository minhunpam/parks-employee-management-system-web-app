import re
from urllib.parse import parse_qs, urlparse


DRIVE_FOLDER_URL_PATTERN = re.compile(r"/folders/([^/?#]+)")
SPREADSHEET_URL_PATTERN = re.compile(r"/spreadsheets/d/([^/?#]+)")

def parse_resource_id(value: str, resource_type: str) -> str:
    """Extract a Drive folder or Sheets spreadsheet ID from an ID or URL."""
    value = value.strip()
    if not value:
        raise ValueError("A resource ID or URL is required.")

    pattern = (
        DRIVE_FOLDER_URL_PATTERN
        if resource_type == "folder"
        else SPREADSHEET_URL_PATTERN
    )
    match = pattern.search(value)
    if match:
        return match.group(1)

    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc:
        query_id = parse_qs(parsed.query).get("id", [None])[0]
        if query_id:
            return query_id
        raise ValueError("Enter a valid Google Drive or Sheets URL.")

    return value
