import sys
import re
import traceback
import functools
from urllib.parse import urlparse
from typing import List, Tuple, Any
from time import sleep

import click
import discogs_client  # type: ignore[import]
from termcolor import colored  # type: ignore[import]
from googleapiclient import discovery  # type: ignore[import]

from . import SETTINGS
from .core_gsheets import get_credentials, get_values
from .common_types import WorksheetData, WorksheetRow

update_threshold = 10  # ends the program and updates after these many updates
update_count = 0


@functools.lru_cache(1)
def discogsClient() -> discogs_client.Client:
    return discogs_client.Client(
        SETTINGS.DISCOGS_CREDS["user_agent"], user_token=SETTINGS.DISCOGS_CREDS["token"]
    )


def has_discogs_link(row: WorksheetRow) -> bool:
    """Returns True/False based on whether the entry has a discogs link."""
    if len(row) >= 8:
        return len(row[7].strip()) > 0
    return False


def has_discogs_data(row: WorksheetRow) -> bool:
    """Returns True if discogs data has been scraped for this entry before."""
    if has_discogs_link(row):
        return bool("".join(map(str.strip, row[8:])))
    return False


def discogs_get(_type: str, _id: int) -> Any:
    """Gets data from discogs API."""
    print(f"[Discogs] Requesting {_id}.")
    sleep(2)
    if _type == "master":  # if Master
        return discogsClient().master(_id).main_release
    elif _type == "release":
        return discogsClient().release(_id)
    else:
        raise RuntimeError(f"Unknown discogs request type: {_type}")


def fix_discogs_link(link: str, resolve: bool) -> str:
    """Removes unnecessary parts of Discogs URLs"""
    urlparse_path = urlparse(link).path
    master_id = re.search("\/master\/(?:view\/)?(\d+)", urlparse_path)
    if master_id:  # if we matched master id
        return "https://www.discogs.com/master/{}".format(master_id.groups()[0])
    else:  # if there is no master id
        release_id = master_id = re.search("\/release\/(?:view\/)?(\d+)", urlparse_path)
        if release_id:
            if resolve:
                release_match = release_id.groups()[0]
                print(f"Attempting to resolve release {release_match} to master.")
                rel = discogsClient().release(int(release_match))
                sleep(2)
                if rel.master is not None:
                    print(f"Resolved release {release_match} to {rel.master.id}.")
                    return "https://www.discogs.com/master/{}".format(
                        int(rel.master.id)
                    )
                else:
                    return "https://www.discogs.com/release/{}".format(release_match)
            else:
                return "https://www.discogs.com/release/{}".format(
                    release_id.groups()[0]
                )
        else:
            raise Exception(f"Unknown discogs link: {link}. Exiting...")


def fix_discogs_artist_name(artists: List[Any]) -> Tuple[str, str]:
    """Fixes names if there are duplicates on Discogs.
    Discogs lists some artists with parens after their name to prevent duplicates."""
    artist_ids = [str(a.id) for a in artists if a.id != 0]
    artists_names = [str(a.name) for a in artists]
    artist_fixed_names = [
        re.sub(r"\(\d+\)$", "", name).strip() for name in artists_names
    ]
    return ", ".join(artist_fixed_names), "|".join(artist_ids)


def prompt_changes(old_row: WorksheetRow, new_row: WorksheetRow) -> bool:
    """Asks the user to confirm changes resulting from discogs data."""
    old_row = old_row[1:]
    new_row = new_row[1:]
    changes = []
    for index, (old_item, new_item) in enumerate(zip(old_row, new_row)):
        if (
            old_item is not None
            and len(old_item.strip()) != 0
            and str(old_item).strip().lower() != str(new_item).strip().lower()
        ):
            changes.append(f"'{old_item}' → '{new_item}'")
    if changes:
        print("\n".join([colored("CONFIRM CHANGES:", "red")] + changes))
        return click.confirm("Confirm Changes? ")
    else:  # changes don't have to be confirmed, continue with changes
        return True


def update_row_with_discogs_data(row, max_length):
    """Gets values from discogs API and prompts the user to confirm changes."""
    link = row[7]
    _type, id = urlparse(link).path.strip("/").split("/")
    while len(row) < max_length:
        row.append("")
    original_row = list(row)
    rel = discogs_get(_type, int(id))
    row[1] = rel.title  # Album Name
    row[2], row[8] = fix_discogs_artist_name(rel.artists)  # Artist Name
    row[3] = rel.year  # Year
    if row[3] == 0:  # discogs API returns 0 if year was unknown for master release
        print(
            f"Warning: Failed to get year for {id}: {row[1]}. Using old year ({original_row[3]})."
        )
        row[3] = original_row[3]
    if rel.images is not None:
        row[6] = '=IMAGE("{}")'.format(rel.images[0]["uri"])  # Image
    else:
        row[6] = ""
    # Genres
    row[9] = ", ".join(sorted(set(rel.genres if rel.genres is not None else [])))
    # Style
    row[10] = ", ".join(sorted(set(rel.styles if rel.styles is not None else [])))
    artist_ids = set([person.id for person in rel.credits if person.id != 0])
    row[11] = "|".join(map(str, artist_ids))  # Credit Artist IDs
    if prompt_changes(original_row, row):
        return row
    else:
        return original_row


def _fix_row(row: WorksheetRow, max_no_of_columns: int, resolve: bool) -> WorksheetRow:
    """Updates with Discogs data if necessary."""
    if has_discogs_link(row):  # if this has a discogs link
        row[7] = fix_discogs_link(row[7], resolve)  # fix link
        if not has_discogs_data(row):  # if theres no data for this yet
            row = update_row_with_discogs_data(row, max_no_of_columns)
    return row


def fix_rows(values: WorksheetData, resolve: bool) -> WorksheetData:
    """Error Handling, exits cleanly on exceptions."""
    header = values.pop(0)
    max_no_of_columns = len(header)
    all_links = set()

    for index, row in enumerate(values):
        row = list(map(str, row))
        try:
            values[index] = _fix_row(row, max_no_of_columns, resolve)
        except discogs_client.exceptions.HTTPError:
            if "429" in str(discogs_client.exceptions.HTTPError):
                wait_time = 30
                print(f"[Discogs] API Limit Reached. Waiting {wait_time} seconds...")
                sleep(wait_time)
            else:
                traceback.print_exc()  # non rate-limit related error
                break
        except:
            traceback.print_exc()  #  other error
            break

        # check for duplicate links, i.e. duplicate entries
        if has_discogs_link(row):
            if row[7] not in all_links:
                all_links.add(row[7])
            else:  # exit if theres a duplicate discogs link (meaning duplicate entry)
                print(f"Found duplicate of {row[7]}. Exiting...")
                break

    values.insert(0, header)  # put header back
    return values


def update_values(values, credentials):
    """Updates the values on the spreadsheet"""
    # Uses batchUpdate instead of update since its difficult to format 'date listened on' from FORMULA valueRenderOption
    service = discovery.build(
        "sheets", "v4", credentials=credentials, cache_discovery=False
    )
    no_of_rows = len(values)
    update_data = [
        {
            # Album, Artist, Year
            "range": "Music!B1:D{}".format(no_of_rows),
            "values": [vals[1:4] for vals in values],
        },
        {
            # Album Artwork, Discogs Link, Artist ID(s), Genre, Style, Credits (ID)
            "range": "Music!F1:L{}".format(no_of_rows),
            "values": [vals[5:] for vals in values],
        },
    ]
    update_body = {
        "valueInputOption": "USER_ENTERED",  # to allow images to display
        "data": update_data,
    }
    request = (
        service.spreadsheets()
        .values()
        .batchUpdate(spreadsheetId=SETTINGS.SPREADSHEET_ID, body=update_body)
    )
    return request.execute()


def update_new_entries(resolve: bool) -> None:
    credentials = get_credentials()
    values = get_values(
        credentials=credentials, sheetRange="Music!A1:L", valueRenderOption="FORMULA"
    )
    if len(values) == 0:
        print("No values returned")
        sys.exit(1)
    response = update_values(values=fix_rows(values, resolve), credentials=credentials)
    print("Updated {} cells.".format(response["totalUpdatedCells"]))
