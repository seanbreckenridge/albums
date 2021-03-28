import os
from typing import Optional, Any

import click
import httplib2
from googleapiclient import discovery
from oauth2client.file import Storage

from . import SETTINGS


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    exits, and tells user to run setup script.
    """
    store = Storage(SETTINGS.CREDENTIALS_PATH)
    credentials = store.get()
    if not credentials or credentials.invalid:
        click.echo(
            """Credentials aren't setup properly. Run 'python3 setup_credentials.py'
If the problem persists, delete {} and then try again""".format(
                SETTINGS.CREDENTIALS_PATH
            ),
            err=True,
        )
        sys.exit(1)
    return credentials


def get_values(*, sheetRange: str, valueRenderOption: str, credentials: Optional[Any] = None):
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
    return result.get("values", [])
