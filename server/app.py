"""Creates MySQL compliant SQL statements to create a schema with current album data from the spreadsheet"""

import sys
import os
import re
from typing import List, Any

import httplib2
import xlrd
import yaml
from googleapiclient import discovery
from flask import Flask, jsonify

app = Flask(__name__)

this_dir = os.path.dirname(__file__)
root_dir = os.path.join(this_dir, os.pardir)
sql_dir = os.path.join(root_dir, "SQL")

arist_data = []


def load_artist_data():
    global arist_data
    with open(os.path.join(sql_dir, "score_artist_cache.yaml")) as data:
        artist_data = yaml.load(data, Loader=yaml.FullLoader)
    return artist_data


sys.path.insert(0, root_dir)

from nextalbums import get_credentials, spreadsheet_id


def make_request() -> List[List[Any]]:
    """
    crude way of keeping this up to date -- Re-create the credential/service
    each time a request is made, so that the credentials are valid

    returns the results array of arrays
    """
    http = get_credentials().authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?version=v4')
    service = discovery.build('sheets',
                              'v4',
                              http=http,
                              discoveryServiceUrl=discoveryUrl)
    return service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="A1:L",
        valueRenderOption="FORMULA").execute().get("values", [])


def split_item_list(comma_seperated: str) -> List[str]:
    """
    Split comma separated string into list
    """
    # special case, since it has commas in it
    return_names = []
    if "Folk, World, & Country" in comma_seperated:  # special case, has commas in it.
        comma_seperated = comma_seperated.replace("Folk, World, & Country", "")
        return_names.append('Folk, World, & Country')

    for description in re.split(r"\s*,\s*", comma_seperated):
        if description.strip():
            return_names.append(description.strip())
    return return_names


class album:

    attrs = [
        "score", "album_name", "cover_artist", "listened_on", "album_artwork",
        "discogs_url", "reasons", "genres", "styles", "main_artists",
        "other_artists"
    ]

    def __init__(self, vals: List):

        #  add empty rows to places where spreadsheet had no values
        while len(vals) < 12:
            vals.append("")
        score, album_name, artists_on_album_cover, year, date, reasons, album_artwork, \
            discogs_url, main_artists, genres, styles, credits = map(str, vals)
        try:
            self.score = float(score)
        except ValueError:  # could be empty or 'can't find'
            self.score = None
        self.album_name = album_name
        self.cover_artist = artists_on_album_cover
        self.year = int(year)
        if date.strip():
            if self.score is None:
                print(
                    "WARNING: {} ({}) has no 'score' but has a 'listened on' date"
                    .format(self.album_name, self.cover_artist))
            self.listened_on = xlrd.xldate_as_datetime(int(date), 0)
        else:
            if self.score is not None:
                print(
                    "WARNING: {} ({}) has no 'listened on' date but has a 'score'"
                    .format(self.album_name, self.cover_artist))
            self.listened_on = None
        self.album_artwork = re.search(r"https?://[^\"]+", album_artwork)
        if self.album_artwork:
            self.album_artwork = self.album_artwork.group(0)
        else:
            self.album_artwork = None
            print("Warning. No Album Artwork extracted from '{}' for '{}'".
                  format(album_artwork, album_name))
        self.discogs_url = discogs_url if discogs_url.strip() else None

        self.reasons = split_item_list(reasons)
        self.genres = split_item_list(genres)
        self.styles = split_item_list(styles)

        self.main_artists = []
        for main_id in main_artists.strip().split("|"):
            if main_id.strip():
                self.main_artists.append(int(main_id.strip()))

        self.other_artists = []
        for other_id in credits.strip().split("|"):
            if other_id.strip():
                self.other_artists.append(int(other_id.strip()))

    def __repr__(self) -> str:
        return "{}({})".format(
            self.__class__.__name__, ", ".join([
                "{}={}".format(attr, repr(getattr(self, attr)))
                for attr in self.__class__.attrs
            ]))

    __str__ = __repr__

    def to_dict(self) -> str:
        return {attr: getattr(self, attr) for attr in self.__class__.attrs}


def request_albums() -> List[album]:
    resp = make_request()
    if resp:
        return [album(a) for a in resp[1:]]
    else:
        return []


@app.route("/", methods=["GET", "POST"])
def handler():
    albums = request_albums()
    return jsonify([a.to_dict() for a in albums])


if __name__ == "__main__":
    app.run()
