### albums

A collection of CSV/SQL files containing popular/acclaimed albums, used to make a inordinate list of albums to listen to.

This contains code to interact with my [spreadsheet](https://sean.fish/s/albums) -- listing the next albums I should listen to, validating the data using the Discogs API, or creating a SQL schema with the data

If you just want the data, see [`csv_data`](./csv_data) and [`sql_data`](./sql_data) for the sources/data. [`spreadsheets.csv`](./spreadsheet.csv) can be used to make your own spreadsheet, [`sql_data/statements.sql`](sql_data/statements.sql) is similar to that for SQL. I update these files periodically, whenever I update my own spreadsheet

![](./.github/images/diagram.png)

### nextalbums

The command that is installed by following the instructions below:

```
Usage: nextalbums [OPTIONS] COMMAND [ARGS]...

  Interact with my albums spreadsheet!

Options:
  --help  Show this message and exit.

Commands:
  create-sql-statements  Creates MySQL compliant SQL statements to create a...
  discogs-update         Update rows on the spreadsheet which just have a...
  favorites              List my favorites using the SQL Database
  generate-csv           Generate the spreadsheet.csv file in the root dir
  print-next             Print the next albums I should listen to
  update-csv-datafiles   Updates the CSV files in data directory
```

- `nextalbums discogs-update` uses the [Discogs API](https://github.com/discogs/discogs_client) to fetch and validate the data on [the spreadsheet](https://docs.google.com/spreadsheets/d/12htSAMg67czl8cpkj1mX0TuAFvqL_PJLI4hv1arG5-M/edit#gid=1451660661)
- `nextalbums favorites` queries my favorite albums using the live SQL instance
- `nextalbums generate-csv` updates [`spreadsheet.csv`](./spreadsheet.csv) file
- `nextalbums update-csv-datafiles` queries the live SQL instance to update the files in [`csv_data`](./csv_data)

This entire process is managed by me using `./update`, which calls those in the required order to update all the datafiles here

The part of this I use most often is `nextalbums print-next`, which prints the next albums from the spreadsheet I should listen to:

```
$ nextalbums print-next
+--------------------------------+---------------------------+------+
| Album                          | Artist                    | Year |
+--------------------------------+---------------------------+------+
| Aqua City                      | S. Kiyotaka & Omega Tribe | 1983 |
| F-1 Grand Prix World           | T-Square                  | 1992 |
| Serendipity 18                 | The Bob Florence Limited  | 1998 |
|                                | Edition                   |      |
| The Miseducation Of Lauryn     | Lauryn Hill               | 1998 |
| Hill                           |                           |      |
| This Is Hardcore               | Pulp                      | 1998 |
| This Is My Truth Tell Me Yours | Manic Street Preachers    | 1998 |
| Vol. 2... Hard Knock Life      | Jay-Z                     | 1998 |
| Vuelve                         | Ricky Martin              | 1998 |
| Wide Open Spaces               | Dixie Chicks              | 1998 |
| 13                             | Blur                      | 1999 |
+--------------------------------+---------------------------+------+
```

### Sources for `spreadsheet.csv`:

Note for '1001 Albums You Must Hear Before You Die' and 'Rolling Stone's 500 Greatest Albums of All Time', the number of albums is above 1001 and 500 respectively, as there have been multiple versions of the book, and I've included anything that was ever on the list.

Note: The 'Rolling Stone's 500 Greatest of All Time' is a combination of the 2012 and earlier versions.

[`csv_data`](csv_data) also contains 3 files that list albums I added [Manually](csv_data/Manual.csv), on a [Recommendation](csv_data/Recommendation.csv), or because of a [Relation](csv_data/Relation.csv) (I liked an artist so I added more of their works). These albums are not listed in `spreadsheet.csv`

The format of all files in [csv_data](csv_data) except for [`all.csv`](csv_data/all.csv) and [`valid_albums.csv`](csv_data/valid_albums.csv) is:

`Album Name, Artists on Cover, Year, DiscogsURL, Genres, Styles`

`all.csv` contains albums I added manually, by relation, or on a recommendation, while `valid_albums.csv` does not. These CSV files also have a column that lists the Reason(s) the album is on the spreadsheet.

### Installation:

Configuration for this is handled by modifying the `settings.py` file in this directory. Since that is just a python file, you're free to modify that to pull items out of environment variables (`os.environ["ENVIRONMENT_VAR"]`) or anything else. You can run the file (`python3 settings.py`) to print the computed settings

1. Create your own copy of the [spreadsheet](https://docs.google.com/spreadsheets/d/12htSAMg67czl8cpkj1mX0TuAFvqL_PJLI4hv1arG5-M/edit#gid=1451660661). You can open a new [google sheet](https://docs.google.com/spreadsheets/u/0/), and then File > Import [`spreadsheet.csv`](spreadsheet.csv) into a new google sheet. I'd also recommend setting a fixed row height to ensure images are all the same size (You can do this by doing Ctrl/⌘ + A repeatedly till the margins are selected, and then resizing one row to your desired height.) Name the sheet 'Music' (near the bottom right)
2. Clone this repository `git clone https://github.com/seanbreckenridge/albums`, and install it using `pip install --editable .`, installing it as an editable package. This **wont** work as normal `pip install`, it must be editable
3. Create a file named `client_secret.json` in the root directory which contains your credentials for a google sheets OAuth connection. [Tutorial here](https://console.developers.google.com); download your created credentials from [here](https://console.developers.google.com/apis/credentials)
4. Run `python3 setup_credentials.py` to setup the Google credentials
5. Update the SPREADSHEET_ID variable in `settings.py` (along with any other settings you see fit)
6. (If you want to add albums and validate them with `discogs_update.py`) Create a file `discogs_token.yaml` in the root directory (info can be found [here](https://www.discogs.com/developers/), token [here](https://www.discogs.com/settings/developers)) with contents similar to:

```
user_agent: myPython3DiscogsClient/1.0
token: !!str FDJjksdfJkJFDNMoiweiIRWkj
```

### SQL

`nextalbums create-sql-statements` creates a file `statements.sql` that when run would create the following schema:

<img src="https://raw.githubusercontent.com/seanbrecke/albums/master/.github/images/diagram.png" alt="" width=600>

It can be run with the flag `--use-scores`, which adds the "Score" and "Listened On" columns to the "Album" Table, and creates the file `score_statements.sql`

Running it _without_ the `--use-scores` flag is close to what `statements.csv` in the root directory chooses as valid albums - only albums that have won at least 1 award, disregarding any albums I added to the spreadsheet manually, by relation, or on a recommendation.

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

### server

[`server`](./server) includes a flask server which grabs current information from spreadsheet:

```
'/' endpoint
get scored albums based on a few filters:
GET args:
limit=int, default 50
orderby=score|listened_on, default score
sort=asc|desc, defeault desc
```

```
'/artist' endpoint GET arg:
ids=id1,id2,id3,id4
(discogs artist IDs, which are returned in the response of '/')
```

Thats cached periodically and used to pull recent albums I've listened onto my 'Media Feed' window [on my website](https://sean.fish/)
