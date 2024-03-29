import sys
import textwrap
import itertools
import random
import shutil

from prettytable import PrettyTable  # type: ignore[import]

from .core_gsheets import get_values
from .common import WorksheetData, eprint


def generate_table(count: int, choose_random: bool) -> str:
    terminal_width = shutil.get_terminal_size().columns
    allow_width = terminal_width // 3

    text_wrapper = textwrap.TextWrapper(
        # allow table decoration
        width=allow_width,
        drop_whitespace=True,
        placeholder="...",
        max_lines=3,
    )

    # grab values from sheet
    values: WorksheetData = get_values(
        sheetRange="Music!A1:D", valueRenderOption="FORMATTED_VALUE"
    )
    if not values:
        eprint("No Values returned from Google API.")
        sys.exit(1)

    header = values.pop(0)[1:]  # pop header from values

    # setup pretty table
    p_table = PrettyTable()
    p_table.field_names = header  # set header
    for header_name in header:
        p_table.align[header_name] = "l"  # align left

    not_listened_to: WorksheetData = [
        [album, artist, year]
        for (score, album, artist, year) in values
        if not score.strip()
    ]

    if choose_random:
        random.shuffle(not_listened_to)

    for row in itertools.islice(not_listened_to, count):
        p_table.add_row(["\n".join(text_wrapper.wrap(x)) for x in row])

    return str(p_table)
