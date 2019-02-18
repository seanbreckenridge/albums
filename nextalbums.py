import httplib2
from googleapiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

import os
import re
import sys
import csv
import argparse
import textwrap
import webbrowser
from random import randint
from distutils.util import strtobool
from itertools import chain

from prettytable import PrettyTable

# location to save --csv output to.
CSV_OUTPUT_FILE = 'spreadsheet.csv'
PREV_CALL_FILE = os.path.join(os.path.dirname(__file__), ".prev_call")

spreadsheet_id = '12htSAMg67czl8cpkj1mX0TuAFvqL_PJLI4hv1arG5-M'
pageId = '1451660661'

wrapper = textwrap.TextWrapper(width=30, drop_whitespace=True, placeholder="...", max_lines=3)


def format_for_table(r):
    """Formats a row for the table, breaking the text into multiple lines if its above 25 characters in length."""
    return ["\n".join(wrapper.wrap(x)) for x in r]


def parse_command_line_args():
    """Parses arguments from user and exits if count is not valid."""
    parser = argparse.ArgumentParser(
        prog='python3 nextalbums.py',
        description="List the Next Albums to listen to.",
        formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=30))
    parser.add_argument("-n", type=int,
                        help="Changes the number of albums to return." +
                        " Default is 10.", default=10)
    parser.add_argument("-r", "--random", action="store_true",
                        help="Chooses random albums instead " +
                        "of listing chronologically.")
    parser.add_argument("-o", "--open", action="store_true",
                        help="Open the cell that corresponds "
                        "to the next album in the " +
                        "spreadsheet online. " +
                        "Ignored if choosing randomly.")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="quiet mode - only print errors.")
    parser.add_argument("-m", "--memory", action="store_true",
                        help="Open the spreadsheet online based " +
                        "on the previous call to next albums " +
                        "and quit. This is much faster since " +
                        "it doesn't require an API call" +
                        "(the line stored in '.prev_call')")
    parser.add_argument("--csv", action="store_true",
                        help="Generates a CSV file without " +
                        "any scores/'listened on' dates.")
    args = parser.parse_args()
    #  make sure count is valid
    if args.n < 1:
        print("Count must be bigger than 0.", file=sys.stderr)
        sys.exit(1)
    if args.memory:
        args.open = False # don't open twice
        args.quiet = True
    # redirect stdout to os.devnull if quiet mode is activated:
    if args.quiet:
        sys.stdout = open(os.devnull, 'w')
    
    return args.n, args.random, args.open, args.csv, args.memory


def csv_and_exit(values):
    """Generates a CSV File with order:
    Album, Artist, Year, Awards, Discogs Link, Genre, Style, Credits (ID)

    Exits the program after completion.
    """

    csv_dir = os.path.dirname(__file__)  # directory nextalbums module was loaded
    csv_fullpath = os.path.join(csv_dir, CSV_OUTPUT_FILE)
    if os.path.exists(csv_fullpath):
        try:
            print(f"{csv_fullpath} already exists, overwrite it?", end=" ", file=sys.stderr)
            user_response = input().strip()
            if not strtobool(user_response):
                sys.exit(1)
        except ValueError:
            print(f"Could not interpret '{user_response}' as a response. \n" +
                  "True values are y, yes, t, true, on and 1; false values are n, no, f, false, off and 0.",
                  file=sys.stderr)
            sys.exit(1)

    values = list(list(chain(row[:3], [row[4]], row[6:])) for row in values)

    values = [row for row in values if not
              set(map(lambda s: s.lower(), re.split("\s*,\s*", row[3])))
              .issubset(set(["manual", "relation", "recommendation"]))]

    with open(csv_fullpath, 'w') as csv_file:
        csv_writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL)
        for row in values:
            # write '' to empty cells, to make all the row lengths in the csv file the same
            csv_writer.writerow(list(chain(row, ['' for empty_cells in range(max(map(len, values)) - len(row))])))
        print(f"Wrote to {csv_fullpath} successfully.")
    sys.exit(0)


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    exits, and tells user to run setup script.

    Returns:
        Credentials, the obtained credential.
    """
    credential_dir = os.path.join(os.path.expanduser('~'), '.credentials')
    if not os.path.exists(credential_dir):
        print('Credentials have not been setup properly. Run setup.py', file=sys.stderr)
        sys.exit(1)
    credential_path = os.path.join(
                credential_dir, 'sheets.googleapis.com-python-nextalbums.json')
    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        print('Credentials have not been setup properly. Run setup.py.\n' +
              'If the problem persists, delete {0} and run setup.py again.'.format(
               credential_path), file=sys.stderr)
        sys.exit(1)
    return credentials

if __name__ == "__main__":

    count, choose_random, open_in_browser, make_csv, open_from_memory = parse_command_line_args()

    if open_from_memory:
        try:
            with open(PREV_CALL_FILE) as prev_f:
                prev_album_cell = prev_f.read().strip()
            webbrowser.open("https://docs.google.com/spreadsheets/d/{0}/edit#gid={1}&range=A{2}"
            .format(spreadsheet_id, pageId, prev_album_cell))
        except: # no previous call
            open_in_browser = True # failed to open, use API
            
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?version=v4')
    service = discovery.build('sheets', 'v4', http=http, discoveryServiceUrl=discoveryUrl)

    rangeName = 'A1:D'
    if make_csv:
        rangeName = 'B2:K'

    result = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=rangeName).execute()
    values = result.get('values', [])

    if not values:
        print('No Values returned from Google API.', file=sys.stderr)
        sys.exit(1)
    if make_csv:
        csv_and_exit(values)
    header = values.pop(0)[1:]  # pop header from values
    p_table = PrettyTable()
    p_table.field_names = header  # set header
    for header_name in header:
        p_table.align[header_name] = 'l'  # align left

    not_listened_to = [tuple((i, [album, artist, year]))
                       for i, (score, album, artist, year) in enumerate(values)
                       if not score.strip()]
    # tuple is so we can link to location in spreadsheet later.

    if choose_random:  # random choice
        while count and not_listened_to:
            p_table.add_row(format_for_table(
                            not_listened_to.pop(randint(0, len(not_listened_to) - 1))[1]))
            count -= 1
    else:  # chronological
        for index in range(count):
            if index < len(not_listened_to):
                if index == 0:
                    link_range = not_listened_to[index][0] + 2
                    #  + 2 is accounting for header
                    #  and the fact that sheets starts from 1 instead of 0.
                    with open(PREV_CALL_FILE, 'w') as call_f:
                        call_f.write(f"{link_range}")
                p_table.add_row(format_for_table(not_listened_to[index][1]))

        if open_in_browser and not choose_random:
            webbrowser.open_new_tab(
                "https://docs.google.com/spreadsheets/d/{0}/edit#gid={1}&range=A{2}"
                .format(spreadsheet_id, pageId, link_range))
    print(p_table)
