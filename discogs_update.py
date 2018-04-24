import httplib2
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
from googleapiclient import discovery
import discogs_client
from distutils.util import strtobool

from nextalbums import get_credentials

import sys
import re
import traceback
from urllib.parse import urlparse
from json import load
from time import sleep

spreadsheet_id = '12htSAMg67czl8cpkj1mX0TuAFvqL_PJLI4hv1arG5-M'
d_Client = None
update_threshold = 10   # ends the program and updates after these many updates
update_count = 0


def discogs_token():
    """Load User-Agent and token from json file."""
    with open('discogs_token.json') as f:
        discogs_cred = load(f)
    return discogs_cred["user_agent"], discogs_cred["token"]


def init_discogs_client():
    """Initialize the discogs API Client."""
    global d_Client
    user_agent, token = discogs_token()
    d_Client = discogs_client.Client(user_agent, user_token=token)


def has_discogs_link(row):
    """Returns True/False based on whether the entry has a discogs link."""
    if len(row) >= 8:
        return len(row[7].strip()) > 0
    return False


def has_discogs_data(row):
    """Returns True if discogs data has been scraped for this entry before."""
    if has_discogs_link(row):
        return bool("".join(map(str.strip, row[8:])))
    return False


def discogs_get(_type, id):
    """Gets data from discogs API."""
    global d_Client
    global update_count
    print(f"[Discogs] Requesting {id}.")
    sleep(2)
    update_count += 1
    if _type == "master":  # if Master
        return d_Client.master(id).main_release
    elif _type == "release":
        return d_Client.release(id)
        sleep(2)
        if rel.master is not None:
            return rel.master.main_release
        else:
            print(f"Release {id} has no master release.")
            return rel
    else:
        raise Excepion(f"Unknown discogs request type: {_type}")


def fix_discogs_link(link):
    """Removes unnecessary parts of Discogs URLs"""
    urlparse_path = urlparse(link).path
    master_id = re.search("\/master\/(?:view\/)?(\d+)", urlparse_path)
    if master_id:  # if we matched master id
        return "https://www.discogs.com/master/{}".format(master_id.groups()[0])
    else:  # if there is no master id
        release_id = master_id = re.search("\/release\/(?:view\/)?(\d+)", urlparse_path)
        if release_id:
            release_match = release_id.groups()[0]
            print(f"Attempting to resolve release {release_match} to master.")
            rel = d_Client.release(int(release_match))
            sleep(2)
            if rel.master is not None:
                print(f"Resolved release {release_match} to {rel.master.id}.")
                return "https://www.discogs.com/master/{}".format(int(rel.master.id))
            else:
                return "https://www.discogs.com/release/{}".format(release_match)
        else:
            raise Exception(f"Unknown discogs link: {link}. Exiting...")


def fix_discogs_artist_name(artists):
    """Fixes names if there are duplicates on Discogs.
    Discogs lists some artists with parens after their name to prevent duplicates."""
    artist_ids = [str(a.id) for a in artists]
    artists_names = [str(a.name) for a in artists]
    artist_fixed_names = [re.sub(r"\(\d+\)$", "", name).strip() for name in artists_names]
    return ", ".join(artist_fixed_names), "|".join(artist_ids)


def prompt_changes(old_row, new_row):
    """Asks the user to confirm changes resulting from discogs data."""
    global update_count
    old_row = old_row[1:]
    new_row = new_row[1:]
    changes = []
    for index, (old_item, new_item) in enumerate(zip(old_row, new_row)):
        if old_item is not None and len(old_item.strip()) != 0 \
                and str(old_item).strip().lower() != str(new_item).strip().lower():
            changes.append(f"'{old_item}' → '{new_item}'")
    if changes:
        print("\n".join([colored("CONFIRM CHANGES:", "red")] + changes))
        return strtobool(input("Confirm Changes? "))
    else:  # changes don't have to be confirmed, continue with changes
        return True


def update_row_with_discogs_data(row, max_length):
    """Gets values from discogs API and prompts the user to confirm changes."""
    global d_Client
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
        print(f"Warning: Failed to get year for {id}: {row[1]}. Using old year ({original_row[3]}).")
        row[3] = original_row[3]
    row[6] = '=IMAGE("{}")'.format(rel.images[0]["uri"])  # Image
    row[9] = ", ".join(sorted(set(rel.genres if rel.genres is not None else [])))  # Genres
    row[10] = ", ".join(sorted(set(rel.styles if rel.styles is not None else [])))  # Style
    artist_ids = set([person.id for person in rel.credits])
    row[11] = "|".join(map(str, artist_ids))  # Credit Artist IDs
    if prompt_changes(original_row, row):
        return row
    else:
        return original_row


def _fix_row(row, max_no_of_columns):
    """Updates with Discogs data if necessary."""
    if has_discogs_link(row):  # if this has a discogs link
        row[7] = fix_discogs_link(row[7])  # fix link
        if not has_discogs_data(row):  # if theres no data for this yet
            row = update_row_with_discogs_data(row, max_no_of_columns)
    return row


def fix_rows(values):
    """Error Handling, exits cleanly on exceptions."""
    global update_count
    header = values.pop(0)
    max_no_of_columns = len(header)
    all_links = set()

    for index, row in enumerate(values):
        row = list(map(str, row))
        if update_count > update_threshold:  # if we've updated enough entries
            print("Hit update threshold; updating spreadsheet.")
            break

        try:
            values[index] = _fix_row(row, max_no_of_columns)
        except discogs_client.exceptions.HTTPError as discogs_api_limit:
            if '429' in str(discogs_client.exceptions.HTTPError):
                wait_time = 30
                print(f"[Discogs] API Limit Reached. Waiting {wait_time} seconds...")
                sleep(wait_time)
            else:
                traceback.print_exc() # non rate-limit related error
                break
        except:
            traceback.print_exc() # other error
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


def get_values(credentials):
    """Gets the values from the spreadsheet"""
    http = credentials.authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?version=v4')
    service = discovery.build('sheets', 'v4', http=http, discoveryServiceUrl=discoveryUrl)
    # valueRendorOption = FORMULA is needed so we can keep images. Cells are blank or else.
    result = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range="A1:L", valueRenderOption="FORMULA").execute()
    return result.get('values', [])


def update_values(values, credentials):
    """Updates the values on the spreadsheet"""
    # Uses batchUpdate instead of update since its difficult to format listened on from FORMULA valueRenderOption
    service = discovery.build('sheets', 'v4', credentials=credentials)
    no_of_rows = len(values)
    update_data = [
        {
            # Album, Artist, Year
            'range': "Music!B1:D{}".format(no_of_rows),
            'values': [vals[1:4] for vals in values]
        },
        {
            # Album Artwork, Discogs Link, Artist ID(s), Genre, Style, Credits (ID)
            'range': "Music!G1:L{}".format(no_of_rows),
            'values': [vals[6:] for vals in values]
        }
    ]
    update_body = {
        'valueInputOption': "USER_ENTERED",  # to allow images to display
        'data': update_data
    }
    request = service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id, body=update_body)
    return request.execute()


def main():
    init_discogs_client()
    credentials = get_credentials()
    values = get_values(credentials)
    if len(values) == 0:
        print("No values returned")
    else:
        values = fix_rows(values)
        response = update_values(values, credentials)
        print("Updated {} cells.".format(response["totalUpdatedCells"]))

if __name__ == "__main__":
    main()
