import os

import click

from . import SETTINGS
from .generate_table import generate_table
from .discogs_update import update_new_entries
from .update_datafiles import update_datafiles, write_to_spreadsheets_csv_file
from .export import export_data, dump_results
from .common import eprint


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """
    Interact with my albums spreadsheet!
    """
    # run print-next if I didn't specify anything else
    if ctx.invoked_subcommand is None:
        ctx.invoke(print_next)


@main.command(short_help="print next albums")
@click.argument("COUNT", default=10, type=int)
@click.option("-r", "--random", is_flag=True, default=False, help="Print random albums")
def print_next(count: int, random: bool) -> None:
    """Print the next albums I should listen to"""
    click.echo(generate_table(count, random))


@main.command(short_help="export sheet as JSON")
@click.option(
    "-r",
    "--raise-errors",
    is_flag=True,
    default=False,
    help="If there are any errors while exporting, exit",
)
def export(raise_errors: bool) -> None:
    """Parse and print all of the information from the spreadsheet as JSON"""
    items = []
    for res in export_data():
        if isinstance(res, Exception):
            if raise_errors:
                raise res
            eprint(str(res))
        else:
            items.append(res)
    click.echo(dump_results(items))


@main.command(short_help="use discogs to update sheet")
@click.option(
    "-r",
    "--resolve-to-master",
    "_resolve",
    is_flag=True,
    default=False,
    help="Attempt to resolve release IDs to Master on Discogs",
)
def discogs_update(_resolve: bool) -> None:
    """
    Update rows on the spreadsheet which just have a discogs link

    Gets information from the Discogs API
    """
    updated: int = update_new_entries(_resolve)
    eprint(f"Updated {updated} cells")


@main.command(short_help="update csv datafiles")
def update_csv_datafiles() -> None:
    """Updates the CSV files in data directory"""
    update_datafiles()


@main.command(short_help="update spreadsheet.csv")
def generate_csv() -> None:
    """Generate the spreadsheet.csv file in the root dir"""
    with open(SETTINGS.BASE_SPREADSHEETS_CSV_FILE, "w") as f:
        write_to_spreadsheets_csv_file(f)
    sfile = SETTINGS.BASE_SPREADSHEETS_CSV_FILE
    if sfile.startswith(os.environ["HOME"]):
        sfile = "~" + sfile[len(os.environ["HOME"]) :]
    eprint(f"Wrote to {sfile} successfully.")


if __name__ == "__main__":
    main(prog_name="nextalbums")
