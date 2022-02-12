import re
import string
from dataclasses import dataclass, replace
from urllib.parse import urlparse
from typing import List, Any, Set, Dict
from time import sleep

import backoff  # type: ignore[import]
import httplib2  # type: ignore[import]
from googleapiclient import discovery  # type: ignore[import]

from . import SETTINGS
from .core_gsheets import get_credentials, get_values
from .common import WorksheetData, WorksheetRow, eprint
from .discogs_cache import fetch_discogs, backoff_hdlr, discogsClient
from .export import export_data, Album, _split_separated


def _pad_data(row: WorksheetRow, col_count: int) -> WorksheetRow:
    while str(row[-1]).strip() == "":
        row.pop(-1)
    while len(row) < col_count:
        row.append("")
    assert len(row) == col_count
    return row


@dataclass
class AlbumInfo:
    score: str
    album: str
    artist: str
    year: str
    listened_on: str
    reason: str
    album_artwork: str
    discogs_url: str
    main_artist_id: str
    genres: str
    styles: str

    @classmethod
    def from_row(cls, row: WorksheetRow) -> "AlbumInfo":
        strd = [
            str(c) for c in _pad_data(row, len(list(AlbumInfo.__annotations__.keys())))
        ]
        return cls(*strd)

    def has_discogs_link(self) -> bool:
        return bool(self.discogs_url.strip())

    def to_row(self) -> List[str]:
        fields = list(AlbumInfo.__annotations__.keys())
        vals: List[str] = []
        for f in fields:
            vals.append(getattr(self, f))
        assert len(vals) == 11, str(vals)
        return vals


def _fix_discogs_link(link: str, resolve: bool) -> str:
    """Removes unnecessary parts of Discogs URLs"""
    urlparse_path = urlparse(link).path
    if master_id := re.search("\/master\/(?:view\/)?(\d+)", urlparse_path):
        return "https://www.discogs.com/master/{}".format(master_id.groups()[0])
    else:  # if there is no master id
        if release_id := re.search("\/release\/(?:view\/)?(\d+)", urlparse_path):
            if resolve:
                release_match = release_id.groups()[0]
                eprint(f"Attempting to resolve release {release_match} to master.")
                rel = discogsClient().release(int(release_match))
                sleep(2)
                if rel.master is not None:
                    eprint(f"Resolved release {release_match} to {rel.master.id}.")
                    return f"https://www.discogs.com/master/{rel.master.id}"
                else:
                    return "https://www.discogs.com/release/{}".format(release_match)
            else:
                return f"https://www.discogs.com/release/{release_id.groups()[0]}"
        else:
            raise Exception(f"Unknown discogs link: {link}. Exiting...")


ARTIST_NAME_REGEX = re.compile(r"\(\d+\)$")


def _fix_artist_name(artist_name: str) -> str:
    return str(re.sub(ARTIST_NAME_REGEX, "", artist_name)).strip()


def _artist_ids(artists: List[Dict[str, Any]]) -> str:
    artist_ids = [str(a["id"]) for a in artists if int(a["id"]) != 0]
    return "; ".join(artist_ids)


ASK_FIELDS = list(AlbumInfo.__annotations__.keys())
ASK_FIELDS.remove("score")
ASK_FIELDS.remove("listened_on")


def print_changes(old_info: AlbumInfo, new_info: AlbumInfo) -> None:
    """Asks the user to confirm changes resulting from discogs data."""
    printed_album_info: bool = False
    for field in ASK_FIELDS:
        old_data = getattr(old_info, field)
        new_data = getattr(new_info, field)
        if str(old_data) != str(new_data):
            if not printed_album_info:
                print(f"\n{new_info}\n")
                printed_album_info = True
            eprint(f"'{old_data}' → '{new_data}'")


# titles like '4:30', time of day, get malformed because gsheets thinks its math
TIME_DIGITS = set(string.digits + ":")


def _escape_title(title: str) -> str:
    if set(title).issubset(TIME_DIGITS) or "!" in title or "'" in title or '"' in title:
        return f'=T("{title}")'
    return title


def _discogs_image(album: Album) -> str | None:
    for d in album.datas():
        if image_list := d.get("images"):
            assert isinstance(image_list, list)
            for d in image_list:
                return '=IMAGE("{}")'.format(d["uri"])
    return None


def discogs_update_info(info: AlbumInfo, album: Album | Exception) -> AlbumInfo:
    """Gets values from discogs API and prompts the user to confirm changes."""

    new_info = replace(info)  # copy dataclass
    link = info.discogs_url
    assert link.strip(), str(info)
    metadata: Dict[str, Any] = fetch_discogs(link).metadata

    assert "title" in metadata
    assert "artists" in metadata
    assert isinstance(metadata["artists"], list), str(metadata)

    new_info.album = _escape_title(metadata["title"])
    assert len(metadata["artists"]) > 0, str(metadata)
    new_info.main_artist_id = _artist_ids(metadata["artists"])
    new_info.artist = ", ".join(
        [_fix_artist_name(artist["name"]) for artist in metadata["artists"]]
    )

    if isinstance(album, Album):
        new_info.year = str(album.release_date().year)

    if isinstance(album, Album):
        if img_cell := _discogs_image(album):
            new_info.album_artwork = img_cell
        else:
            new_info.album_artwork = info.album_artwork

    new_info.genres = "; ".join(sorted(set(metadata.get("genres", []))))
    new_info.styles = "; ".join(sorted(set(metadata.get("styles", []))))

    print_changes(info, new_info)
    return new_info


def non_discogs_update(info: AlbumInfo, album: Album | Exception) -> AlbumInfo:
    new_info = replace(info)  # copy dataclass
    new_info.genres = "; ".join(_split_separated(info.genres))
    new_info.styles = "; ".join(_split_separated(info.styles))

    print_changes(info, new_info)
    return new_info


def upkeep(info: AlbumInfo, album: Album | Exception) -> AlbumInfo:
    new_info = replace(info)  # copy dataclass
    new_info.reason = "; ".join(_split_separated(info.reason))

    print_changes(info, new_info)
    return new_info


def update_row(info: AlbumInfo, album: Album | Exception, *, resolve: bool) -> AlbumInfo:
    """Updates with Discogs data if necessary."""
    if info.has_discogs_link():  # if this has a discogs link
        info.discogs_url = _fix_discogs_link(info.discogs_url, resolve)
        info = discogs_update_info(info, album)
    else:
        info = non_discogs_update(info, album)
    info = upkeep(info, album)
    return info


def updates(values: WorksheetData, resolve: bool) -> WorksheetData:
    """Error Handling, exits cleanly on exceptions."""
    header = values.pop(0)
    all_links: Set[str] = set()

    albums: List[Album | Exception ] = list(export_data(data_source=values, remove_header=False))

    for index, (album, row) in enumerate(zip(albums, values, strict=True)):
        info: AlbumInfo = AlbumInfo.from_row(row)
        if isinstance(album, Exception):
            print(info)
            print(album)
        if not isinstance(album, Exception) and info.discogs_url:
            assert (
                album.discogs_url == info.discogs_url
            ), f"{album.discogs_url} != {info.discogs_url}"
        info = update_row(info, album, resolve=resolve)
        values[index] = info.to_row()

        # check for duplicate links, i.e. duplicate entries
        if info.has_discogs_link():
            if info.discogs_url not in all_links:
                all_links.add(info.discogs_url)
            else:  # exit if theres a duplicate discogs link (meaning duplicate entry)
                eprint(f"Found duplicate of {info.discogs_url}. Exiting...")
                break

    values.insert(0, header)  # put header back
    return values


@backoff.on_exception(
    lambda: backoff.constant(interval=10),
    httplib2.error.ServerNotFoundError,
    max_tries=5,
    on_backoff=backoff_hdlr,
)
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
            "values": [_pad_data(vals[1:4], 3) for vals in values],
        },
        {
            # Album Artwork, Discogs Link, Artist ID(s), Genre, Style, Credits (ID)
            "range": "Music!F1:K{}".format(no_of_rows),
            "values": [_pad_data(vals[5:], 6) for vals in values],
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


def update_new_entries(resolve: bool) -> int:
    """Returns the number of cells updated"""
    credentials = get_credentials()
    values = get_values(
        credentials=credentials,
        sheetRange="Music!A1:K",
        valueRenderOption="FORMULA",
        remove_escapes=False,
    )
    if len(values) == 0:
        eprint("No values returned")
        raise SystemExit(1)
    response = update_values(values=updates(values, resolve), credentials=credentials)
    return int(response["totalUpdatedCells"])
