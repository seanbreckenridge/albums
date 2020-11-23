#!/usr/bin/env python3

"""
Basic script to list out my favorite albums
I have an alias that runs this and opens up sc-im:

alias favorite-albums='python3 ~/Repos/albums/favorites.py > /tmp/favorites.csv && sc-im /tmp/favorites.csv'
"""

import sys
import os

this_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(this_dir, "src"))

import csv

from datetime import datetime
from typing import List, Sequence

from _update_from_db import create_connection


def main():
    db = create_connection()
    c = db.cursor()
    c.execute(
        'SELECT CONCAT(Album.Name, " - ", Album.CoverArtists, " (", Album.Year, ")"), Album.Score\
        FROM Album WHERE SCORE IS NOT NULL ORDER BY Album.Score DESC'
    )
    rows = [("Description", "Score")]
    rows.extend(list(map(list, c.fetchall())))

    writer = csv.writer(sys.stdout, delimiter=",", quoting=csv.QUOTE_ALL)
    for r in rows:
        writer.writerow(r)


if __name__ == "__main__":
    main()
