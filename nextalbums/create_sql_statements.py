import sys
import re
import os
import time
from typing import List, Dict, Any, Optional, NamedTuple

import yaml
import click
import discogs_client  # type: ignore[import]
import xlrd  # type: ignore[import]


from . import SETTINGS
from .common import split_comma_separated, eprint, filter_personal_reasons


def sql_datafile(path: str) -> str:
    """Gets an absolute path to a file in SQL data directory"""
    return os.path.join(SETTINGS.SQL_DATADIR, path)


from .core_gsheets import get_values
from .discogs_update import discogsClient


class AutoIncrementAnalog:
    """class to manage a variable number of reasons/genres/styles, and connecting them to surrogate ids"""

    def __init__(self):
        # e.g., name of reason -> reason id
        self.keymap: Dict[str, int] = {}

    def add(self, desc: str) -> int:
        """description (e.g. Rock/1001 Albums/Funk) to add to the list. Returns the ID this description belongs to"""
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

    def add_comma_separated_list(self, comma_separated: str) -> List[int]:
        return_ids: List[int] = []
        for name in split_comma_separated(comma_separated):
            return_ids.append(self.add(name))
        return return_ids


class APICache:
    """class to manage caching API requests for artist names"""

    def __init__(self, yaml_path: str):
        self.yaml_path = yaml_path
        self.write_to_cache_const = 25
        self.write_to_cache_periodically = self.write_to_cache_const
        if not os.path.exists(self.yaml_path):
            open(self.yaml_path, "a").close()
        with open(self.yaml_path, "r") as js_f:
            try:
                self.items = yaml.load(js_f, Loader=yaml.FullLoader)
                eprint(f"[Cache] {len(self.items)} items loaded from cache.")
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
        eprint(f"[Discogs] Downloading name for id {id}")
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
        # Various Artists; this doesnt have a page on discogs, its just a placeholder
        if str(id) == "194":
            self.items[194] = "Various"
            return self.items[194]
        if self.__contains__(id):
            eprint("[Cache] Found name for id {} in cache".format(id))
            return self.items[int(id)]
        else:
            self.items[int(id)] = self.download_name(id)
            return self.items[int(id)]

    def put(self, id, name):
        self.items[int(id)] = str(name)

    def __iter__(self):
        return self.items.__iter__()


class Context(NamedTuple):
    artist_cache: APICache
    reasons_table: AutoIncrementAnalog
    genres_table: AutoIncrementAnalog
    styles_table: AutoIncrementAnalog


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

    def __init__(self, vals: List[Any], *, ctx: Context):
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
        self.score: Optional[float]
        try:
            self.score = float(score)
        except:  # could be empty or 'can't find'
            self.score = None
        self.album_name: str = album_name
        self.cover_artist: str = artists_on_album_cover
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
        self.album_artwork: Optional[str]
        aa = re.search('https?:\/\/[^"]+', album_artwork)
        if aa:
            self.album_artwork = aa.group(0)
        else:
            self.album_artwork = None
            eprint(
                f"Warning. No Album Artwork extracted from '{album_artwork}' for '{album_name}'"
            )
        self.discogs_url = discogs_url if discogs_url.strip() else None

        self.reason_id: List[int] = ctx.reasons_table.add_comma_separated_list(reasons)
        self.genre_id: List[int] = ctx.genres_table.add_comma_separated_list(genres)
        self.style_id: List[int] = ctx.styles_table.add_comma_separated_list(styles)

        # loop over both main and other artists
        self.main_artists: List[str] = []
        self.other_artists: List[str] = []
        for (artist_list, celled_list) in (
            (self.main_artists, main_artists),
            (self.other_artists, credits),
        ):
            # from the google sheet, like 4934|439434|9293011
            for artist_id in celled_list.strip().split("|"):
                artist_id = artist_id.strip()
                if len(artist_id) > 0:
                    if artist_id not in ctx.artist_cache:
                        # download name so we can get it from cache later
                        ctx.artist_cache.get(artist_id)
                    artist_list.append(artist_id)


def statements(
    albums: List[album],
    *,
    use_score: bool,
    base_table_file: str,
    statement_file: str,
    ctx: Context,
) -> None:

    ctx.artist_cache.update_yaml_file()

    statements = []  # SQL statements that would add data to the database

    # create artist SQL statements
    indexed_artists = {}

    for index, artist in enumerate(iter(ctx.artist_cache), 1):
        indexed_artists[index] = {
            "discogs_url": "https://www.discogs.com/artist/{}".format(artist),
            "name": ctx.artist_cache.items[artist],
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
        ("Reason", ctx.reasons_table),
        ("Genre", ctx.genres_table),
        ("Style", ctx.styles_table),
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
        for short_name, type_ids in [
            ("Reason", a.reason_id),
            ("Genre", a.genre_id),
            ("Style", a.style_id),
        ]:  #  for each descriptor
            for id in type_ids:  # for each id this album has for this descriptor
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

    artist_cache_filepath = sql_datafile("artist_cache.yaml")
    score_artist_cache_filepath = sql_datafile("score_artist_cache.yaml")

    values = get_values(sheetRange="A1:L", valueRenderOption="FORMULA")

    if use_scores:
        # add items that may have been added to the base cache to prevent duplicate API calls
        eprint("Loading base artist cache...")
        base_cache = APICache(artist_cache_filepath)
        eprint("Loading score artist cache...")
        artist_cache = APICache(score_artist_cache_filepath)
        for id in base_cache:
            if id not in artist_cache:
                artist_cache.put(id, base_cache.get(id))
    else:
        eprint("Loading base artist cache...")
        artist_cache = APICache(artist_cache_filepath)

    tables_file = sql_datafile("base_tables.sql")
    output_file = sql_datafile("statements.sql")
    score_tables_file = sql_datafile("score_base_tables.sql")
    score_output_file = sql_datafile("score_statements.sql")

    ctx = Context(
        artist_cache=artist_cache,
        reasons_table=AutoIncrementAnalog(),
        genres_table=AutoIncrementAnalog(),
        styles_table=AutoIncrementAnalog(),
    )

    if bool(values) is False:
        eprint("No values returned from Google API")
        sys.exit(1)
    else:
        if use_scores:
            albums = [album(list(val), ctx=ctx) for val in values[1:]]
            statements(
                albums,
                use_score=True,
                base_table_file=score_tables_file,
                statement_file=score_output_file,
                ctx=ctx,
            )
        else:
            albums = [
                album(list(val), ctx=ctx) for val in filter_personal_reasons(values)
            ]
            statements(
                albums,
                use_score=False,
                base_table_file=tables_file,
                statement_file=output_file,
                ctx=ctx,
            )
