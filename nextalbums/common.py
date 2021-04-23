import re

from functools import partial, lru_cache
from typing import Any, List

import click

WorksheetValue = Any
WorksheetRow = List[WorksheetValue]
WorksheetData = List[WorksheetRow]

eprint = partial(click.echo, err=True)

# vendorized from stdlib to work in under python3.9
def cache(user_function):
    'Simple lightweight unbounded cache.  Sometimes called "memoize".'
    return lru_cache(maxsize=None)(user_function)


@cache
def split_comma_separated(comma_separated: str) -> List[str]:
    """Split comma separated string into list"""
    return_names = []
    # special case for genres, since it has commas in it
    if "Folk, World, & Country" in comma_separated:
        comma_separated = comma_separated.replace("Folk, World, & Country", "")
        return_names.append("Folk, World, & Country")

    for description in re.split(r"\s*,\s*", comma_separated):
        if description.strip():
            return_names.append(description.strip())
    return return_names


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
