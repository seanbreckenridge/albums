#!/usr/bin/env python3

"""
Basic script to list out my favorite albums
I have an alias that runs this and opens up sc-im:

alias favorite_albums='python3 ~/code/albums/favorites.py > /tmp/favorites.csv && sc-im /tmp/favorites.csv'
"""

import sys
import os

this_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(this_dir, "src"))

import csv

from datetime import datetime
from typing import List, Sequence

from _update_from_db import create_connection


def format_row(row_tuple: Sequence) -> List:
    """
    Converts the tuple from the db to printable list
    """
    row_l = list(row_tuple)
    for i, x in enumerate(row_l):
        if not isinstance(x, datetime):
            row_l[i] = str(row_l[i])
        else:
            row_l[i] = datetime.strftime(row_l[i], "%Y-%m-%d")
    return row_l


def main():
    db = create_connection()
    c = db.cursor()
    c.execute(
        "SELECT Album.Name, Album.CoverArtists, Album.Year, Album.Score,\
Album.ListenedOn FROM Album WHERE SCORE IS NOT NULL ORDER BY Album.Score DESC"
    )
    rows = [("Name", "Artists", "Year", "Score", "ListenedOn")]
    rows.extend(list(map(format_row, c.fetchall())))

    writer = csv.writer(sys.stdout, delimiter=",", quoting=csv.QUOTE_ALL)
    for r in rows:
        writer.writerow(r)


if __name__ == "__main__":
    main()
