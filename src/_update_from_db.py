import os
import re
import csv
import operator

import MySQLdb


def create_connection():

    db = MySQLdb.connect(
        host="localhost", db="scorealbums", user="sean", password="sean"
    )
    return db


def write_csv(name, results):
    with open(name, "w") as reason_file:
        csv_writer = csv.writer(reason_file, quoting=csv.QUOTE_MINIMAL)
        csv_writer.writerows(results)


def main():

    db = create_connection()
    c = db.cursor()

    c.execute("SELECT ReasonID, Description FROM Reason")
    # For each reason for being on the spreadsheet
    for id, desc in sorted(c.fetchall(), key=operator.itemgetter(1)):
        c.execute(
            """
SELECT Name, CoverArtists, Year, DiscogsURL, GROUP_CONCAT(DISTINCT Genre.Description SEPARATOR "|"), GROUP_CONCAT(DISTINCT Style.Description SEPARATOR "|")
FROM Album
JOIN AlbumReason
  ON Album.AlbumID = AlbumReason.AlbumID
JOIN Reason
  ON AlbumReason.ReasonID = Reason.ReasonID
LEFT JOIN AlbumGenre
  ON Album.AlbumID = AlbumGenre.AlbumID
LEFT JOIN Genre
  ON AlbumGenre.GenreID = Genre.GenreID
LEFT JOIN AlbumStyle
  ON Album.AlbumID = AlbumStyle.AlbumID
LEFT JOIN Style
  ON AlbumStyle.StyleID = Style.StyleID
WHERE Reason.ReasonID = %s
GROUP BY Album.AlbumID
ORDER BY Year, Name""",
            (id,),
        )
        results = c.fetchall()

        # reformat reason to be a decent filename
        desc = desc.strip().replace("'", "")
        desc = re.sub("[\s&/]", "_", desc)
        filename = os.path.join(os.path.dirname(__file__), desc)

        write_csv(f"{filename}.csv", results)

    # all albums, with reasons
    c.execute(
        """
SELECT Name, CoverArtists, Year, DiscogsURL, GROUP_CONCAT(DISTINCT Reason.Description SEPARATOR "|"), GROUP_CONCAT(DISTINCT Genre.Description SEPARATOR "|"), GROUP_CONCAT(DISTINCT Style.Description SEPARATOR "|")
FROM Album
JOIN AlbumReason
  ON Album.AlbumID = AlbumReason.AlbumID
JOIN Reason
  ON AlbumReason.ReasonID = Reason.ReasonID
LEFT JOIN AlbumGenre
  ON Album.AlbumID = AlbumGenre.AlbumID
LEFT JOIN Genre
  ON AlbumGenre.GenreID = Genre.GenreID
LEFT JOIN AlbumStyle
  ON Album.AlbumID = AlbumStyle.AlbumID
LEFT JOIN Style
  ON AlbumStyle.StyleID = Style.StyleID
GROUP BY Album.AlbumID
ORDER BY Year, Name
"""
    )
    results = c.fetchall()
    write_csv("all.csv", results)

    # all albums excluding ones I added manually, on a recommendation, or relation, with reason
    c.execute(
        """
SELECT Name, CoverArtists, Year, DiscogsURL, GROUP_CONCAT(DISTINCT Reason.Description SEPARATOR "|"), GROUP_CONCAT(DISTINCT Genre.Description SEPARATOR "|"), GROUP_CONCAT(DISTINCT Style.Description SEPARATOR "|")
FROM Album
JOIN AlbumReason
  ON Album.AlbumID = AlbumReason.AlbumID
JOIN Reason
  ON AlbumReason.ReasonID = Reason.ReasonID
LEFT JOIN AlbumGenre
  ON Album.AlbumID = AlbumGenre.AlbumID
LEFT JOIN Genre
  ON AlbumGenre.GenreID = Genre.GenreID
LEFT JOIN AlbumStyle
  ON Album.AlbumID = AlbumStyle.AlbumID
LEFT JOIN Style
  ON AlbumStyle.StyleID = Style.StyleID
WHERE Reason.Description <> "Manual" AND
Reason.Description <> "Relation" AND
Reason.Description <> "Recommendation"
GROUP BY Album.AlbumID
ORDER BY Year, Name
"""
    )
    results = c.fetchall()
    write_csv("valid_albums.csv", results)


if __name__ == "__main__":
    main()
