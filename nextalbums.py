import httplib2
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

import os
import argparse
from random import randint
from sys import exit, stderr
import webbrowser
import csv
import textwrap

from prettytable import PrettyTable

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/sheets.googleapis.com-python-nextalbums.json
SCOPES = 'https://www.googleapis.com/auth/spreadsheets.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Next Albums'
wrapper = textwrap.TextWrapper(width=44, drop_whitespace=True, placeholder="...", max_lines=3)

def format_for_table(r):
    """Formats a row for the table, breaking the text into multiple lines if its above 25 characters in length."""
    return ["\n".join(wrapper.wrap(x)) for x in r]

def parse():
    """does argparsing"""
    parser = argparse.ArgumentParser(
        description="Get the Next Albums to listen to.")
    parser.add_argument("-c", "--count", type=int,
                        help="Changes the number of albums to return." +
                        " Default is 10.")
    parser.add_argument("-r", "--random", action="store_true",
                        help="Chooses random albums instead " +
                        "of listing chronologically.")
    parser.add_argument("-o", "--open", action="store_true",
                        help="Open the cell that corresponds "
                        "to the next album in the " +
                        "spreadsheet online. " +
                        "Ignored if choosing randomly.")
    parser.add_argument("--csv", action="store_true",
                        help="Generates a CSV file without " +
                        "any scores/'listened on' dates.")
    args = parser.parse_args()
    if args.count is None:
        count = 10
    else:
        if args.count > 0:
            count = args.count
        else:
            print("Count must be bigger than 0.", file=stderr)
            exit(1)
    return count, args.random, args.open, args.csv

def csv_and_exit(values):
    """Generates a CSV File with order:
    Album, Artist, Year, Awards

    Exits the program after completion.
    """
    for row in values:
        del row[3] # remove 'date listened on'
    values = [row for row in values if not "manual" in row[-1].lower()]
    # some albums I added manually which have no reason to be here otherwise
    with open('spreadsheet.csv', 'w') as csv_file:
        csv_writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL)
        for row in values:
            csv_writer.writerow(row)
    exit(0)


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(
                credential_dir, 'sheets.googleapis.com-python-nextalbums.json')
    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
    return credentials

if __name__ == "__main__":

    count, choose_random, open_in_browser, make_csv = parse()

    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?version=v4')
    service = discovery.build('sheets', 'v4', http=http, discoveryServiceUrl=discoveryUrl)

    spreadsheetId = '12htSAMg67czl8cpkj1mX0TuAFvqL_PJLI4hv1arG5-M'
    pageId = '1451660661'

    rangeName = 'A1:D'
    if make_csv:
        rangeName = 'B2:F'

    result = service.spreadsheets().values().get(spreadsheetId=spreadsheetId, range=rangeName).execute()
    values = result.get('values', [])

    if not values:
        print('No Values returned from Google API.')
    else:
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
                                not_listened_to.pop(
                                randint(0, len(not_listened_to) - 1))[1]))
                count -= 1
        else:  # chronological
            for index in range(count):
                if index < len(not_listened_to):
                    if index == 0:
                        link_range = not_listened_to[index][0] + 2
                        #  + 2 is accounting for header
                        #  and the fact that sheets starts from 1 instead of 0.
                    p_table.add_row(format_for_table(not_listened_to[index][1]))

        if open_in_browser and not choose_random:
            webbrowser.open(
                "https://docs.google.com/spreadsheets/d/{0}/edit#gid={1}&range&range=A{2}"
                .format(spreadsheetId, pageId, link_range), new=2)
        print(p_table)
