import re
import csv
from pathlib import Path
from typing import List, Set, Iterator, TextIO, Optional


from . import SETTINGS
from .common import WorksheetData, WorksheetRow, filter_personal_reasons
from .core_gsheets import get_values
from .export import Album, export_data


def write_csv(name: str, results: WorksheetData, *, key: Optional[str] = None) -> None:
    path = Path(SETTINGS.CSV_DATADIR)
    if key is not None:
        path /= key
    path /= name
    path.parent.mkdir(parents=True, exist_ok=True)
    max_row_len = max(map(len, results))
    with open(path, "w") as reason_file:
        csv_writer = csv.writer(reason_file, quoting=csv.QUOTE_ALL)
        for row in results:
            padded = row + [""] * (max_row_len - len(row))
            # remove score/listened on, image rows
            rrow = [v for i, v in enumerate(padded) if i not in {0, 4, 6}]
            csv_writer.writerow(rrow)


def _iter_descriptor(albums: List[Album], key: str) -> Set[str]:
    descriptors: Set[str] = set()
    for a in albums:
        data = getattr(a, key)
        assert isinstance(data, list)
        for val in data:
            assert isinstance(val, str)
            descriptors.add(val)
    return descriptors


def _filter_by_descriptor(
    values: List[WorksheetData], albums: List[Album], key: str, descriptor: str
) -> Iterator[WorksheetRow]:
    assert len(values) == len(albums)
    for v, a in zip(values, albums):
        val = getattr(a, key)
        assert isinstance(val, list)
        if descriptor in val:
            yield v


def update_datafiles():
    values = get_values(sheetRange="Music!A2:K", valueRenderOption="FORMULA")
    albums = list(export_data(data_source=values, remove_header=False))
    for a in albums:
        if isinstance(a, Exception):
            raise a

    for key in {"reasons"}:
        for descriptor in _iter_descriptor(albums, key):
            desc = re.sub("[\s&/]", "_", descriptor)
            rows = list(_filter_by_descriptor(values, albums, key, descriptor))
            write_csv(f"{desc}.csv", rows, key=key)

    write_csv("all.csv", values)


def write_to_spreadsheets_csv_file(buf: TextIO) -> None:
    values = get_values(sheetRange="Music!A2:K", valueRenderOption="FORMULA")
    values = filter_personal_reasons(values)
    csv_writer = csv.writer(buf, quoting=csv.QUOTE_ALL)
    max_row_len = max(map(len, values))
    for row in values:
        # write '' to empty cells, to make all the row lengths in the csv file the same
        padded = row + [""] * (max_row_len - len(row))
        # remove score and listened on dates
        padded[0] = ""
        padded[4] = ""
        csv_writer.writerow(padded)
