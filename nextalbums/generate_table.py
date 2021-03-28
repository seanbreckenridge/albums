import sys
import textwrap
import itertools
import random

import click
from prettytable import PrettyTable  # type: ignore[import]

from .core_gsheets import get_values
from .common_types import WorksheetRow, WorksheetData


text_wrapper = textwrap.TextWrapper(
    width=30, drop_whitespace=True, placeholder="...", max_lines=3
)


def format_for_table(r: WorksheetRow) -> WorksheetRow:
    """Formats a row for the table, breaking the text into multiple lines if its above 25 characters in length."""
    return ["\n".join(text_wrapper.wrap(x)) for x in r]


def generate_table(count: int, choose_random: bool) -> str:

    # grab values from sheet
    values: WorksheetData = get_values(
        sheetRange="Music!A1:D", valueRenderOption="FORMATTED_VALUE"
    )
    if not values:
        click.echo("No Values returned from Google API.", err=True)
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
        p_table.add_row(format_for_table(row))

    return str(p_table)
