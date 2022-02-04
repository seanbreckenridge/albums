import re

from functools import partial
from typing import Any, List

import click

WorksheetValue = Any
WorksheetRow = List[WorksheetValue]
WorksheetData = List[WorksheetRow]

eprint = partial(click.echo, err=True)


# Items which are on my spreadsheet because I added it
# not because they won a award/were on a list etc.
PERSONAL = set(["manual", "relation", "recommendation"])


def _is_personal(data: str) -> bool:
    return set(map(str.lower, re.split(r"\s*,\s*", data))).issubset(PERSONAL)


def filter_personal_reasons(
    data: WorksheetData, strip_header: bool = False
) -> WorksheetData:
    """
    Remove any albums from the data I may have listened to because I wanted to,
    on a recommendation or relation
    """
    values = data[1:] if strip_header else data
    return [row for row in values if not _is_personal(row[5])]
