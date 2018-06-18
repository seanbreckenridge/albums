## Converts the current spreadsheet into a SQL database.

`python3 create_statements.py` creates a file `statements.sql` that when run would create the following schema:

<img src="https://raw.githubusercontent.com/seanbrecke/albums/master/SQL/images/diagram.png" alt="" width=600>

Dependencies: `pip3 install --user --upgrade oauth2client xlrd google-api-python-client discogs_client`

##### Example Queries:

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

Top Jazz Albums:
```SQL
USE albums;
SELECT Album.Name, Album.CoverArtists, Album.Score, Album.ListenedOn
FROM Album 
JOIN AlbumGenre
	ON Album.AlbumID = AlbumGenre.AlbumID
JOIN Genre
	ON AlbumGenre.GenreID = Genre.GenreID
Where Genre.Description = 'Jazz' AND Album.Score IS NOT NULL
ORDER BY Album.Score DESC
;
```

Favorite Genres:
```SQL
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
