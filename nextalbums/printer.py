import os
import sys
import textwrap
import itertools
import random
from functools import lru_cache

import click
from prettytable import PrettyTable


from . import SETTINGS
from .core_gsheets import get_values


text_wrapper = textwrap.TextWrapper(
    width=30, drop_whitespace=True, placeholder="...", max_lines=3
)


def format_for_table(r):
    """Formats a row for the table, breaking the text into multiple lines if its above 25 characters in length."""
    return ["\n".join(text_wrapper.wrap(x)) for x in r]


def print_nextalbums(count: int, choose_random: bool) -> None:

    # grab values from sheet
    values = get_values(sheetRange="Music!A1:D", valueRenderOption="FORMATTED_VALUE")
    if not values:
        click.echo("No Values returned from Google API.", err=True)
        sys.exit(1)
    header = values.pop(0)[1:]  # pop header from values

    # setup pretty table
    p_table = PrettyTable()
    p_table.field_names = header  # set header
    for header_name in header:
        p_table.align[header_name] = "l"  # align left

    not_listened_to = [
        [album, artist, year]
        for (score, album, artist, year) in values
        if not score.strip()
    ]

    if choose_random:
        random.shuffle(not_listened_to)

    for row in itertools.islice(not_listened_to, count):
        p_table.add_row(format_for_table(row))

    click.echo(str(p_table))
