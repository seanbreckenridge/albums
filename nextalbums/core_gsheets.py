from typing import Optional, Any

import httplib2  # type: ignore[import]
from googleapiclient import discovery  # type: ignore[import]
from oauth2client.file import Storage  # type: ignore[import]
from oauth2client.client import OAuth2Credentials  # type: ignore[import]

from . import SETTINGS
from .common import WorksheetData, eprint


def get_credentials() -> OAuth2Credentials:
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    exits, and tells user to run setup script.
    """
    store = Storage(SETTINGS.CREDENTIALS_PATH)
    credentials = store.get()
    if not credentials or credentials.invalid:
        eprint(
            f"""Credentials aren't setup properly. Run 'python3 setup_credentials.py'
If the problem persists, delete {SETTINGS.CREDENTIALS_PATH} and then try again"""
        )
        raise SystemExit(1)
    return credentials


def get_values(
    *, sheetRange: str, valueRenderOption: str, credentials: Optional[Any] = None
) -> WorksheetData:
    creds: Any
    if credentials is None:
        creds = get_credentials()
    else:
        creds = credentials
    http = creds.authorize(httplib2.Http())
    discoveryUrl = "https://sheets.googleapis.com/$discovery/rest?version=v4"
    service = discovery.build(
        "sheets",
        "v4",
        http=http,
        discoveryServiceUrl=discoveryUrl,
        cache_discovery=False,
    )
    result = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=SETTINGS.SPREADSHEET_ID,
            range=sheetRange,
            valueRenderOption=valueRenderOption,
        )
        .execute()
    )
    data: WorksheetData = result.get("values", [])
    return data
