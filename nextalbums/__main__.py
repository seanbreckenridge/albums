import os

import click

from . import SETTINGS
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
    from .generate_table import generate_table

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
    from .export import export_data, dump_results

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
    from .discogs_update import update_new_entries

    updated: int = update_new_entries(_resolve)
    eprint(f"Updated {updated} cells")


@main.command(short_help="update csv datafiles")
def update_csv_datafiles() -> None:
    """Updates the CSV files in data directory"""
    from .update_datafiles import update_datafiles

    update_datafiles()


@main.command(short_help="update spreadsheet.csv")
def generate_csv() -> None:
    """Generate the spreadsheet.csv file in the root dir"""
    from .update_datafiles import write_to_spreadsheets_csv_file

    with open(SETTINGS.BASE_SPREADSHEETS_CSV_FILE, "w") as f:
        write_to_spreadsheets_csv_file(f)
    sfile = SETTINGS.BASE_SPREADSHEETS_CSV_FILE
    home = os.path.expanduser("~")
    if sfile.startswith(home):
        sfile = "~" + sfile[len(home) :]  # noqa
    eprint(f"Wrote to {sfile} successfully.")


@main.command(short_help="override image upload")
@click.argument("ALBUM_ID", type=str)
@click.argument("IMAGE_URL", type=str)
def override_image_upload(album_id: str, image_url: str) -> None:
    """Override the image upload for a specific album"""
    from pathlib import Path
    from urllib.parse import urlparse
    from .image_proxy import (
        image_db,
        _get_image_bytes,
        _get_image_content_type,
        _upload_image,
        s3_bucket,
    )

    db = image_db()
    assert (
        db.exists(album_id)
    ), f"Album ID {album_id} not found in database, should be the key in the JSON file"


    eprint(f"Requesting image from {image_url}")
    image_bytes = _get_image_bytes(image_url)
    if image_bytes is None:
        eprint(f"Could not get image bytes from {image_url}")
        return


    content_type = _get_image_content_type(image_url)
    click.echo(f"Uploading image to S3 bucket {s3_bucket} with content type {content_type}")
    _upload_image(image_bytes, s3_bucket, album_id, content_type)

    assert db.set(album_id, album_id)


if __name__ == "__main__":
    main(prog_name="nextalbums")
