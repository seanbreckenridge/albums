## Converts the current spreadsheet into a SQL database.

`python3 create_statements.py` creates a file `statements.sql` that when run would create the following schema:

<img src="https://raw.githubusercontent.com/seanbrecke/albums/master/SQL/images/diagram.png" alt="" width=600>

It can be run with a flag: `python3 create_statements.py --use-scores`, which adds the "Score" and "Listened On" columns to the "Album" Table, and creates the file `score_statements.sql`.

Running it *without* the `--use-scores` flag is close to what `statements.csv` in the root directory chooses as valid albums - only albums that have won at least 1 award, disregarding any albums I added to the spreadsheet manually, by relation, or on a recommendation.

Dependencies: `pip3 install --user --upgrade oauth2client xlrd google-api-python-client discogs_client`

##### Example Queries:

Anything that's won a grammy award:
```SQL
use albums;
SELECT Album.Name, Album.CoverArtists, Album.Year, GROUP_CONCAT(Reason.Description) as `Awards`
FROM Album
JOIN AlbumReason
	ON Album.AlbumID = AlbumReason.AlbumID
JOIN Reason
	ON AlbumReason.ReasonID = Reason.ReasonID
WHERE Reason.Description LIKE "Grammy%" # Anything that starts with "Grammy"
GROUP BY Album.AlbumID
ORDER BY COUNT(Reason.ReasonID) DESC # order by number of grammy awards
;
```

People who have worked on the most albums:

```SQL
USE albums;
SELECT  Name, artist.works
FROM Artist
JOIN
(
	SELECT Artist_ArtistID, count(Artist_ArtistID) as `works` FROM ArtistWorkedOnAlbum
	GROUP BY Artist_ArtistID
	ORDER BY `works` DESC
) AS artist
ON ArtistID = artist.Artist_ArtistID
WHERE artist.DiscogsArtistURL <> 'https://www.discogs.com/artist/194' -- 194 is various artists
ORDER BY works DESC
;
```

My Favorite Albums from the 80s:
```SQL
USE scorealbums;
SELECT Album.Name, Album.CoverArtists, Album.Year, Album.Score, Album.ListenedOn
FROM Album
WHERE Year > 1979 AND Year < 1990 AND SCORE IS NOT NULL
ORDER BY Album.Score DESC
LIMIT 25
;
```

Favorite Genres:
```SQL
USE scorealbums;
SELECT Genre.Description, AVG(Album.Score) as `Average Score`
FROM Album
JOIN AlbumGenre
	ON Album.AlbumID = AlbumGenre.AlbumID
JOIN Genre
	ON AlbumGenre.GenreID = Genre.GenreID
Where Album.Score IS NOT NULL
GROUP BY Genre.GenreID
ORDER BY `Average Score` DESC
;
```
