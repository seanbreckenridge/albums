import re

from functools import partial, lru_cache
from typing import Any, List

import click

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


WorksheetValue = Any
WorksheetRow = List[WorksheetValue]
WorksheetData = List[WorksheetRow]

eprint = partial(click.echo, err=True)
