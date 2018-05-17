"""Creates MySQL compliant SQL statements to create a schema with current album data from the spreadsheet"""

import sys
sys.path.insert(0, '..')

import httplib2
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
from googleapiclient import discovery
import discogs_client
import xlrd

from nextalbums import get_credentials
from discogs_update import discogs_token

import re
import json
from os import path
from time import sleep

spreadsheet_id = '12htSAMg67czl8cpkj1mX0TuAFvqL_PJLI4hv1arG5-M'
token_filename = path.join(path.normpath('..'), "discogs_token.json")
database_name = "albums.db"
tables_file = "base_tables.sql"
output_file = "statements.sql"

d_Client = None
artist_cache = None
reasons_table = None
genres_table = None
styles_table = None

class autoincrement_analog:
    """class to manage a variable number of reasons/genres/styles, and connecting them to surrogate ids"""

    def __init__(self):
        self.keymap = {}


    def add(self, desc):
        """description (e.g. Rock/1001 Albums/Funk) to add to the list. Returns the ID this description belongs to"""
        # if empty
        if len(self.keymap) == 0:
            self.keymap[desc] = 1
            return self.keymap[desc]
        else:
            if desc not in self.keymap.keys(): # if this isnt in the keymap yet
                new_index = max(list(self.keymap.values())) + 1
                self.keymap[desc] = new_index # add it
                return new_index
            else:
                return self.keymap[desc] # if this was already here, return the index


    def add_comma_seperated_list(self, comma_seperated):
        return_ids = []
        # special case, since it has commas in it
        if "Folk, World, & Country" in comma_seperated:
            comma_seperated = comma_seperated.replace("Folk, World, & Country", "")
            return_ids.append(self.add('Folk, World, & Country'))

        for description in re.split("\s*,\s*", comma_seperated):
            if description.strip():
                return_ids.append(self.add(description.strip()))
        return return_ids

class cache:
    """class to manage caching API requests for artist names"""
    def __init__(self):
        self.jsonpath = 'artist_cache.json'
        self.write_to_cache_const = 5
        self.write_to_cache_periodically = self.write_to_cache_const
        if not path.exists(self.jsonpath):
            open(self.jsonpath, 'a').close()
        with open(self.jsonpath, 'r') as js_f:
            try:
                self.items = json.load(js_f)
            except json.JSONDecodeError: # file is empty or broken
                self.items = {}

    def update_json_file(self):
        with open(self.jsonpath, 'w') as f:
            json.dump(self.items, f)

    def download_name(self, id):
        global d_Client
        self.write_to_cache_periodically -= 1
        if self.write_to_cache_periodically < 0:
            self.write_to_cache_periodically = self.write_to_cache_const
            self.update_json_file()
        print("[Discogs] Downloading name for id {}".format(id))
        sleep(2)
        # change artist names like Sugar (3) to Sugar. Discogs has these names because there may be duplicates for an artist name
        return re.sub(r"\(\d+\)$", "", d_Client.artist(int(id)).name).strip()

    def __contains__(self, id):
        """defines the 'in' keyword on cache."""
        return str(id) in self.items

    def get(self, id):
        if str(id) == "194": # Various Artists; this doesnt have a page on discogs, its just a placeholder
            self.items["194"] = "Various"
            return self.items["194"]
        if self.__contains__(id):
            print("[Cache] Found name for id {} in cache".format(id))
            return self.items[str(id)]
        else:
            self.items[str(id)] = self.download_name(id)
            return self.items[str(id)]

    def __iter__(self):
        return self.items.__iter__()

def escape_apostrophes(input_str):
    """Escapes strings for SQL insert statements"""
    if "'" in input_str:
        return input_str.replace("'", "\\'")
    else:
        return input_str

def quote(input_str):
    """Adds single quotes around a string"""
    return "'{}'".format(input_str)

class album:
    """data for each album"""
    def __init__(self, vals):
        global artist_cache
        global reasons_table
        global styles_table
        global genres_table
        #  add empty rows to places where spreadsheet had no values
        while len(vals) < 12:
            vals.append("")
        score, album_name, artists_on_album_cover, year, date, reasons, album_artwork, \
            discogs_url, main_artists, genres, styles, credits = map(str, vals)
        try:
            self.score = float(score)
        except: # could be empty or 'can't find'
            self.score = None
        self.album_name = album_name
        self.cover_artist = artists_on_album_cover
        self.year = int(year)
        if date.strip():
            self.listened_on = xlrd.xldate_as_datetime(int(date), 0)
            self.listened_on = "{year}-{month}-{day}".format(year=self.listened_on.year,
                    month=self.listened_on.month, day=self.listened_on.day)
        else:
            self.listened_on = None
        self.album_artwork = re.search("https?:\/\/[^\"]+", album_artwork)
        if self.album_artwork:
            self.album_artwork = self.album_artwork.group(0)
        else:
            self.album_artwork = None
            print("Warning. No Album Artwork extracted from {} for {}".format(album_artwork, album_name))
        self.discogs_url = discogs_url if discogs_url.strip() else None

        self.reason_id = reasons_table.add_comma_seperated_list(reasons)
        self.genre_id = genres_table.add_comma_seperated_list(genres)
        self.style_id = styles_table.add_comma_seperated_list(styles)

        self.main_artists = []
        for main_id in main_artists.strip().split("|"):
            if main_id.strip():
                if main_id not in artist_cache:
                    self.main_artists.append(main_id)
                    artist_cache.get(main_id) # download name so we can get it from cache later
                else:
                    self.main_artists.append(main_id)
        self.other_artists = []
        for other_id in credits.strip().split("|"):
            if other_id.strip():
                if other_id not in artist_cache:
                    self.other_artists.append(other_id)
                    artist_cache.get(other_id) # download name so we can get it from cache later
                else:
                    self.other_artists.append(other_id)




def get_values(credentials):
    http = credentials.authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?version=v4')
    service = discovery.build('sheets', 'v4', http=http, discoveryServiceUrl=discoveryUrl)
    result = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range="A1:L", valueRenderOption="FORMULA").execute()
    return result.get("values", [])

def main():
    global artist_cache
    global d_Client
    global reasons_table
    global styles_table
    global genres_table
    user_agent, token = discogs_token(token_filename)
    d_Client = discogs_client.Client(user_agent, user_token=token)
    artist_cache = cache()
    reasons_table = autoincrement_analog()
    genres_table = autoincrement_analog()
    styles_table = autoincrement_analog()
    credentials = get_credentials()
    statements = []
    values = get_values(credentials)
    if values is None:
        print("No values returned from Google API")
    else:
        albums = [album(list(val)) for val in values[1:]]
        artist_cache.update_json_file()

    # create artist SQL statements

    indexed_artists = {}

    for index, artist in enumerate(iter(artist_cache), 1):
        indexed_artists[index] = {"discogs_url": "https://www.discogs.com/artist/{}".format(artist),
            "name": artist_cache.items[artist]}

    for index, vals in indexed_artists.items():
        statements.append("INSERT INTO Artist (ArtistID, DiscogsArtistURL, Name) VALUES ({artistid}, {discogsurl}, {name});".format(
                    artistid=index,
                    discogsurl=quote(vals['discogs_url']),
                    name=quote(escape_apostrophes(vals['name']))
                    ))

    # create album SQL statements

    indexed_albums = {}

    for index, a in enumerate(albums, 1):
        indexed_albums[index] = a

    for index, a in indexed_albums.items():
        statements.append("INSERT INTO Album (AlbumID, Name, CoverArtists, AlbumArtworkURL, DiscogsURL, Score, ListenedOn) " + \
                          "VALUES ({albumid}, {name}, {cover_artists}, {artwork_url}, {discogsurl}, {score}, {listened_on});".format(
                                albumid=index,
                                name=quote(escape_apostrophes(a.album_name)),
                                cover_artists=quote(escape_apostrophes(a.cover_artist)),
                                artwork_url='NULL' if a.album_artwork is None else quote(a.album_artwork),
                                discogsurl='NULL' if a.discogs_url is None else quote(a.discogs_url),
                                score='NULL' if a.score is None else a.score,
                                listened_on='NULL' if a.listened_on is None else quote(a.listened_on)
                            ))

    # add values to artist/album intersection table

    discogs_id_to_artist_id = {}
    for index, vals in indexed_artists.items():
        discogs_id_to_artist_id[vals['discogs_url'].rstrip('/').split('/')[-1]] = index

    for index, a in indexed_albums.items():
        for artist in a.main_artists:
            statements.append("INSERT INTO ArtistWorkedOnAlbum (Album_AlbumID, Artist_ArtistID, Type) " + \
                            "VALUES ({albumid}, {artistid}, 1);".format(
                                albumid=index,
                                artistid=discogs_id_to_artist_id[artist]
                          ))
        for artist in a.other_artists:
            statements.append("INSERT INTO ArtistWorkedOnAlbum (Album_AlbumID, Artist_ArtistID, Type) " + \
                            "VALUES ({albumid}, {artistid}, 0);".format(
                                albumid=index,
                                artistid=discogs_id_to_artist_id[artist]
                          ))

    # create style/genre/reason surrogate tables

    for (table_name, table) in [('Reason', reasons_table), ('Genre', genres_table), ('Style', styles_table)]:
        for description, index in table.keymap.items(): # for each index, description surrogate key pair
            statements.append("INSERT INTO {tbl_name} ({id_column_name}, Description) VALUES ({id}, {desc});".format(
                                tbl_name = table_name,
                                id_column_name = "{}ID".format(table_name),
                                id=index,
                                desc=quote(escape_apostrophes(description))
                            ))

    # add values to style/genre/reason intersection tables

    for index, a in indexed_albums.items(): # for each album
        for short_name, table in [('Reason', a.reason_id), ('Genre', a.genre_id), ('Style', a.style_id)]: # for each descriptor
            for id in table: # for each id this album has for this descriptor
                statements.append("INSERT INTO Album{short_name} (AlbumID, {short_name}ID) VALUES ({album_id}, {id});".format(
                    short_name=short_name,
                    album_id=index,
                    id=id
                ))

    # write to files

    with open(tables_file) as f:
        table_definitions = f.read()

    with open(output_file, 'w') as g:
        g.write("{}\n".format(table_definitions))
        for line in statements:
            g.write("{}\n".format(line))

if __name__ == "__main__":
    main()
