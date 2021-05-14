import json
import re
import datetime
from time import strptime
from pathlib import Path
from typing import NamedTuple, List, Iterator, Optional, Any, Union, Dict

import yaml
import orjson
import xlrd  # type: ignore[import]

from .core_gsheets import get_values
from .common import WorksheetData, split_comma_separated
from .create_sql_statements import sql_datafile
from .common import cache

CANT_FIND = "cant find"

class Artist(NamedTuple):
    artist_id: int
    artist_name: Optional[str]


Note = str


class Album(NamedTuple):
    score: Optional[float]
    note: Optional[Note]  # .e.g some reason I couldn't listen to an album, cant find it
    listened_on: Optional[datetime.date]
    album_name: str
    album_artwork_url: str
    cover_artists: str
    discogs_url: Optional[str]
    year: int
    reasons: List[str]
    genres: List[str]
    styles: List[str]
    main_artists: List[Artist]
    other_artists: List[Artist]


@cache
def read_artist_cache() -> Dict[int, str]:
    with open(sql_datafile("score_artist_cache.yaml")) as f:
        data: Dict[int, str] = yaml.load(f, Loader=yaml.FullLoader)
    return data


@cache
def fetch_artist_name(artist_id: int) -> Artist:
    return Artist(artist_id=artist_id, artist_name=read_artist_cache().get(artist_id))


# optionally can provide a datasource, which returns
# the same data as get_values with the below parameters
# this is so that I have the option to cache the response
# from the get_values function elsewhere, so this
# doen't have to make the API call every time
def export_data(
    data_source: Optional[WorksheetData] = None,
    remove_header: bool = True,
) -> Iterator[Union[Exception, Album]]:
    worksheet_vals: WorksheetData
    if data_source is None:
        worksheet_vals = get_values(sheetRange="Music!A:L", valueRenderOption="FORMULA")
    else:
        worksheet_vals = data_source
    if remove_header:
        worksheet_vals = worksheet_vals[1:]
    for vals in worksheet_vals:
        # pad list incase there are missing values
        while len(vals) < 12:
            vals.append("")
        # destructure row
        (
            score,
            album_name,
            artists_on_album_cover,
            year,
            date,
            reasons,
            album_artwork,
            discogs_url,
            martists,
            genres,
            styles,
            credits,
        ) = list(map(str.strip, map(str, vals)))
        fscore: Optional[float] = None
        note: Optional[str] = None
        try:
            fscore = float(score)
        except:
            # couldn't parse, probably havent listened to this yet
            # edge case, where I can't find an album online
            if score == CANT_FIND:
                note = CANT_FIND
        try:
            iyear = int(year)
        except ValueError as e:
            # yield the error upwards and continue parsing, instead of crashing
            yield e
            continue

        listened_on: Optional[datetime.date] = None
        if date:
            if fscore is None:
                yield RuntimeError(
                    f"{album_name} ({artists_on_album_cover}) has no 'score' but a 'listened on' date"
                )
                continue
            listened_on = xlrd.xldate_as_datetime(int(date), 0).date()
        else:
            if fscore is not None:
                yield RuntimeError(
                    f"{album_name} {artists_on_album_cover} has no 'listened on' date but has a 'score'"
                )
                continue
        artwork: str
        artwork_matches = re.search(r"https?://[^\"]+", album_artwork)
        if artwork_matches:
            artwork = artwork_matches.group(0)
        else:
            yield RuntimeError(
                f"Warning. No Album Artwork extracted from '{album_artwork}' for '{album_name}'"
            )
            continue

        main_artists: List[Artist] = []
        other_artists: List[Artist] = []

        for main_id in martists.split("|"):
            if main_id.strip():
                # really shouldnt fail..., not edited by me
                main_id_int = int(main_id)
                main_artists.append(fetch_artist_name(main_id_int))

        for other_id in credits.strip().split("|"):
            if other_id.strip():
                other_id_int = int(other_id)
                other_artists.append(fetch_artist_name(other_id_int))

        yield Album(
            score=fscore,
            note=note,
            album_name=album_name,
            cover_artists=artists_on_album_cover,
            year=iyear,
            listened_on=listened_on,
            album_artwork_url=artwork,
            discogs_url=discogs_url,
            reasons=split_comma_separated(reasons),
            genres=split_comma_separated(genres),
            styles=split_comma_separated(styles),
            main_artists=main_artists,
            other_artists=other_artists,
        )


def default(o: Any) -> Any:
    # serialize NamedTuple
    if hasattr(o, "_asdict"):
        return o._asdict()
    raise TypeError(f"Couldn't serialize {o}")


def dump_results(data: Any) -> str:
    return orjson.dumps(data, default=default).decode("utf-8")


# helper to read the dump back into list of python object
def read_dump(p: Path) -> Iterator[Album]:
    for blob in json.loads(p.read_text()):
        fscore: Optional[float] = None
        if blob["score"] is not None:
            fscore = float(blob["score"])
        dlistened_on: Optional[datetime.date] = None
        if blob["listened_on"] is not None:
            d = strptime(blob["listened_on"], r"%Y-%m-%d")
            dlistened_on = datetime.date(year=d.tm_year, month=d.tm_mon, day=d.tm_mday)
        yield Album(
            score=fscore,
            note=blob["note"],
            album_name=blob["album_name"],
            cover_artists=blob["cover_artists"],
            year=int(blob["year"]),
            listened_on=dlistened_on,
            album_artwork_url=blob["album_artwork_url"],
            discogs_url=blob["discogs_url"],
            reasons=blob["reasons"],
            genres=blob["genres"],
            styles=blob["styles"],
            main_artists=[Artist(**d) for d in blob["main_artists"]],
            other_artists=[Artist(**d) for d in blob["other_artists"]],
        )
