import re
import csv

from typing import TextIO

from .core_gsheets import get_values
from .common import filter_personal_reasons


def write_to_csv_file(buf: TextIO) -> None:
    values = get_values(sheetRange="Music!A2:L", valueRenderOption="FORMULA")
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
