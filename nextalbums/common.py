from functools import partial
from typing import Any, List

import click

WorksheetValue = Any
WorksheetRow = List[WorksheetValue]
WorksheetData = List[WorksheetRow]

eprint = partial(click.echo, err=True)
