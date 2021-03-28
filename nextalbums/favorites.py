#!/usr/bin/env python3

import sys
import os

import csv

from datetime import datetime
from typing import List, Sequence

from .update_database import create_connection


def list_favorites():
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
