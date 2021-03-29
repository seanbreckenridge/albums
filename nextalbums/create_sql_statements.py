import sys
import re
import os
import time
from typing import List

import yaml
import click
import discogs_client  # type: ignore[import]
import xlrd  # type: ignore[import]


from . import SETTINGS
from .common import eprint


def sql_datafile(path: str) -> str:
    """Gets an absolute path to a file in SQL data directory"""
    return os.path.join(SETTINGS.SQL_DATADIR, path)


from .core_gsheets import get_values
from .discogs_update import discogsClient

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
            if desc not in self.keymap.keys():  # if this isnt in the keymap yet
                new_index = max(list(self.keymap.values())) + 1
                self.keymap[desc] = new_index  # add it
                return new_index
            else:
                return self.keymap[desc]  # if this was already here, return the index

    def add_comma_separated_list(self, comma_separated: str) -> List[str]:
        return_ids = []
        # special case, since it has commas in it
        if (
            "Folk, World, & Country" in comma_separated
        ):  # special case, has commas in it.
            comma_separated = comma_separated.replace("Folk, World, & Country", "")
            return_ids.append(self.add("Folk, World, & Country"))

        for description in re.split("\s*,\s*", comma_separated):
            if description.strip():
                return_ids.append(self.add(description.strip()))
        return return_ids


class cache:
    """class to manage caching API requests for artist names"""

    def __init__(self, yaml_path):
        self.yaml_path = yaml_path
        self.write_to_cache_const = 25
        self.write_to_cache_periodically = self.write_to_cache_const
        if not os.path.exists(self.yaml_path):
            open(self.yaml_path, "a").close()
        with open(self.yaml_path, "r") as js_f:
            try:
                self.items = yaml.load(js_f, Loader=yaml.FullLoader)
                click.echo(
                    "[Cache] {} items loaded from cache.".format(len(self.items))
                )
            except:  # file is empty or broken
                eprint("[Cache] Could not load items.")
                self.items = {}

    def update_yaml_file(self):
        with open(self.yaml_path, "w") as f:
            yaml.dump(self.items, f, default_flow_style=False)

    def download_name(self, id):
        self.write_to_cache_periodically -= 1
        if self.write_to_cache_periodically < 0:
            self.write_to_cache_periodically = self.write_to_cache_const
            self.update_yaml_file()
        click.echo(f"[Discogs] Downloading name for id {id}")
        time.sleep(2)
        # change artist names like Sugar (3) to Sugar. Discogs has these names because there may be duplicates for an artist name
        try:
            return re.sub(r"\(\d+\)$", "", discogsClient().artist(int(id)).name).strip()
        except discogs_client.exceptions.HTTPError:
            eprint(
                f"""Failed to name for download https://www.discogs.com/artist/{id}
That id should be removed from the credits cell, no way around this currently"""
            )
            raise SystemExit(1)

    def __contains__(self, id):
        """defines the 'in' keyword on cache."""
        return int(id) in self.items

    def get(self, id):
        if (
            str(id) == "194"
        ):  # Various Artists; this doesnt have a page on discogs, its just a placeholder
            self.items[194] = "Various"
            return self.items[194]
        if self.__contains__(id):
            click.echo("[Cache] Found name for id {} in cache".format(id))
            return self.items[int(id)]
        else:
            self.items[int(id)] = self.download_name(id)
            return self.items[int(id)]

    def put(self, id, name):
        self.items[int(id)] = str(name)

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
        (
            score,
            album_name,
            artists_on_album_cover,
            year,
            date,
            reasons,
            album_artwork,
            discogs_url,
            main_artists,
            genres,
            styles,
            credits,
        ) = map(str, vals)
        try:
            self.score = float(score)
        except:  # could be empty or 'can't find'
            self.score = None
        self.album_name = album_name
        self.cover_artist = artists_on_album_cover
        self.year = int(year)
        if date.strip():
            if self.score is None:
                eprint(
                    f"WARNING: {self.album_name} ({self.cover_artist}) has no 'score' but has a 'listened on' date"
                )
            self.listened_on = xlrd.xldate_as_datetime(int(date), 0)
            self.listened_on = "{year}-{month}-{day}".format(
                year=self.listened_on.year,
                month=self.listened_on.month,
                day=self.listened_on.day,
            )
        else:
            if self.score is not None:
                eprint(
                    f"WARNING: {self.album_name} ({self.cover_artist}) has no 'listened on' date but has a 'score'"
                )
            self.listened_on = None
        self.album_artwork = re.search('https?:\/\/[^"]+', album_artwork)
        if self.album_artwork:
            self.album_artwork = self.album_artwork.group(0)
        else:
            self.album_artwork = None
            eprint(
                f"Warning. No Album Artwork extracted from '{album_artwork}' for '{album_name}'"
            )
        self.discogs_url = discogs_url if discogs_url.strip() else None

        self.reason_id = reasons_table.add_comma_separated_list(reasons)
        self.genre_id = genres_table.add_comma_separated_list(genres)
        self.style_id = styles_table.add_comma_separated_list(styles)

        self.main_artists = []
        for main_id in main_artists.strip().split("|"):
            if main_id.strip():
                if main_id not in artist_cache:
                    artist_cache.get(
                        main_id
                    )  # download name so we can get it from cache later
                self.main_artists.append(main_id)

        self.other_artists = []
        for other_id in credits.strip().split("|"):
            if other_id.strip():
                if other_id not in artist_cache:
                    artist_cache.get(
                        other_id
                    )  # download name so we can get it from cache later
                self.other_artists.append(other_id)


def statements(albums, use_score, base_table_file, statement_file):
    global artist_cache
    global reasons_table
    global styles_table
    global genres_table
    artist_cache.update_yaml_file()

    statements = []  # SQL statements that would add data to the database

    # create artist SQL statements

    indexed_artists = {}

    for index, artist in enumerate(iter(artist_cache), 1):
        indexed_artists[index] = {
            "discogs_url": "https://www.discogs.com/artist/{}".format(artist),
            "name": artist_cache.items[artist],
        }

    for index, vals in indexed_artists.items():
        statements.append(
            "INSERT INTO Artist (ArtistID, DiscogsArtistURL, Name) VALUES ({artistid}, {discogsurl}, {name});".format(
                artistid=index,
                discogsurl=quote(vals["discogs_url"]),
                name=quote(escape_apostrophes(vals["name"])),
            )
        )

    # create album SQL statements

    indexed_albums = {}

    for index, a in enumerate(albums, 1):
        indexed_albums[index] = a

    if use_score:
        for index, a in indexed_albums.items():
            statements.append(
                "INSERT INTO Album (AlbumID, Name, Year, CoverArtists, AlbumArtworkURL, DiscogsURL, Score, ListenedOn) "
                + "VALUES ({albumid}, {name}, {year}, {cover_artists}, {artwork_url}, {discogsurl}, {score}, {listened_on});".format(
                    albumid=index,
                    name=quote(escape_apostrophes(a.album_name)),
                    year=a.year,
                    cover_artists=quote(escape_apostrophes(a.cover_artist)),
                    artwork_url="NULL"
                    if a.album_artwork is None
                    else quote(a.album_artwork),
                    discogsurl="NULL"
                    if a.discogs_url is None
                    else quote(a.discogs_url),
                    score="NULL" if a.score is None else a.score,
                    listened_on="NULL"
                    if a.listened_on is None
                    else quote(a.listened_on),
                )
            )
    else:
        for index, a in indexed_albums.items():
            statements.append(
                "INSERT INTO Album (AlbumID, Name, Year, CoverArtists, AlbumArtworkURL, DiscogsURL) "
                + "VALUES ({albumid}, {name}, {year}, {cover_artists}, {artwork_url}, {discogsurl});".format(
                    albumid=index,
                    name=quote(escape_apostrophes(a.album_name)),
                    year=a.year,
                    cover_artists=quote(escape_apostrophes(a.cover_artist)),
                    artwork_url="NULL"
                    if a.album_artwork is None
                    else quote(a.album_artwork),
                    discogsurl="NULL"
                    if a.discogs_url is None
                    else quote(a.discogs_url),
                )
            )

    # add values to artist/album intersection table

    discogs_id_to_artist_id = {}
    for index, vals in indexed_artists.items():
        discogs_id_to_artist_id[vals["discogs_url"].rstrip("/").split("/")[-1]] = index

    for index, a in indexed_albums.items():
        for artist in a.main_artists:
            statements.append(
                "INSERT INTO ArtistWorkedOnAlbum (Album_AlbumID, Artist_ArtistID, Type) "
                + "VALUES ({albumid}, {artistid}, 1);".format(
                    albumid=index, artistid=discogs_id_to_artist_id[artist]
                )
            )
        for artist in a.other_artists:
            statements.append(
                "INSERT INTO ArtistWorkedOnAlbum (Album_AlbumID, Artist_ArtistID, Type) "
                + "VALUES ({albumid}, {artistid}, 0);".format(
                    albumid=index, artistid=discogs_id_to_artist_id[artist]
                )
            )

    # create style/genre/reason surrogate ids

    for (table_name, table) in [
        ("Reason", reasons_table),
        ("Genre", genres_table),
        ("Style", styles_table),
    ]:
        for (
            description,
            index,
        ) in table.keymap.items():  # for each index, description surrogate key pair
            statements.append(
                "INSERT INTO {tbl_name} ({id_column_name}, Description) VALUES ({id}, {desc});".format(
                    tbl_name=table_name,
                    id_column_name="{}ID".format(table_name),
                    id=index,
                    desc=quote(escape_apostrophes(description)),
                )
            )

    # add values to style/genre/reason intersection tables

    for index, a in indexed_albums.items():  # for each album
        for short_name, table in [
            ("Reason", a.reason_id),
            ("Genre", a.genre_id),
            ("Style", a.style_id),
        ]:  #  for each descriptor
            for id in table:  # for each id this album has for this descriptor
                statements.append(
                    "INSERT INTO Album{short_name} (AlbumID, {short_name}ID) VALUES ({album_id}, {id});".format(
                        short_name=short_name, album_id=index, id=id
                    )
                )

    # write to files

    with open(base_table_file) as f:
        table_definitions = f.read()

    with open(statement_file, "w") as g:
        g.write("{}\n".format(table_definitions))
        for line in statements:
            g.write("{}\n".format(line))


def create_statments(use_scores: bool) -> None:
    global artist_cache
    global reasons_table
    global styles_table
    global genres_table

    artist_cache_filepath = sql_datafile("artist_cache.yaml")
    score_artist_cache_filepath = sql_datafile("score_artist_cache.yaml")

    values = get_values(sheetRange="A1:L", valueRenderOption="FORMULA")

    if use_scores:
        # add items that may have been added to the base cache to prevent duplicate API calls
        click.echo("Loading base artist cache...")
        base_cache = cache(artist_cache_filepath)
        click.echo("Loading score artist cache...")
        artist_cache = cache(score_artist_cache_filepath)
        for id in base_cache:
            if id not in artist_cache:
                artist_cache.put(id, base_cache.get(id))
    else:
        click.echo("Loading base artist cache...")
        artist_cache = cache(artist_cache_filepath)

    reasons_table = autoincrement_analog()
    genres_table = autoincrement_analog()
    styles_table = autoincrement_analog()

    tables_file = sql_datafile("base_tables.sql")
    output_file = sql_datafile("statements.sql")
    score_tables_file = sql_datafile("score_base_tables.sql")
    score_output_file = sql_datafile("score_statements.sql")

    if bool(values) is False:
        eprint("No values returned from Google API")
        sys.exit(1)
    else:
        if use_scores:
            albums = [album(list(val)) for val in values[1:]]
            statements(albums, True, score_tables_file, score_output_file)
        else:
            # row[5] is the reason
            values = [
                row
                for row in values[1:]
                if not set(
                    map(lambda s: s.lower(), re.split("\s*,\s*", row[5]))
                ).issubset(set(["manual", "relation", "recommendation"]))
            ]
            albums = [album(list(val)) for val in values]
            statements(albums, False, tables_file, output_file)
