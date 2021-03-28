import click

from . import SETTINGS
from .generate_table import generate_table
from .discogs_update import update_new_entries
from .update_database import update_datafiles
from .favorites import list_favorites
from .generate_csv import generate_csv_file
from .create_sql_statements import create_statments
from .export import export_data, dump_results
from .common import eprint


@click.group()
def main():
    """
    Interact with my albums spreadsheet!
    """
    pass


@main.command()
@click.argument("COUNT", default=10, type=int)
@click.option("-r", "--random", is_flag=True, default=False, help="Print random albums")
def print_next(count: int, random: bool) -> None:
    """Print the next albums I should listen to"""
    click.echo(generate_table(count, random))


@main.command()
def export():
    """Parse and print all of the information from the spreadsheet as JSON"""
    items = []
    for res in export_data():
        if isinstance(res, Exception):
            eprint(str(res))
        else:
            items.append(res)
    click.echo(dump_results(items))


@main.command()
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
    click.echo(f"Updated {updated} cells")


@main.command()
def update_csv_datafiles() -> None:
    """Updates the CSV files in data directory"""
    update_datafiles()


@main.command()
def favorites() -> None:
    """
    List my favorites using the SQL Database
    """
    list_favorites()


@main.command()
def generate_csv() -> None:
    """Generate the spreadsheet.csv file in the root dir"""
    generate_csv_file(SETTINGS.BASE_SPREADSHEETS_CSV_FILE)
    click.echo(f"Wrote to {SETTINGS.BASE_SPREADSHEETS_CSV_FILE} successfully.")


@main.command()
@click.option(
    "-s",
    "--use-scores",
    is_flag=True,
    default=False,
    help="If flag is present on command line, adds all albums including scores and date is was listen to on. If the flag is not present, adds all albums, disregarding any albums added manually, by relation, or on a recommendation",
)
def create_sql_statements(use_scores: bool) -> None:
    """Creates MySQL compliant SQL statements to create a schema with current album data from the spreadsheet"""
    create_statments(use_scores)


if __name__ == "__main__":
    main(prog_name="nextalbums")
