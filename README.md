### albums
A collection of csv files containing popular/acclaimed albums, used to make a inordinate list of albums to listen to.

This is a personal project of mine, but I thought I'd leave these files up here in case anyone wanted to use them.

The source csv files are bound to have errors somewhere, e.g. duplicates due to slight differences in album names.

The 'Year' column refers to date released. However, in source csv files for AMA's and Grammies, the year is often the date awarded.

`python3 discogs_update.py` uses the [Discogs API](https://github.com/discogs/discogs_client) to validate the data in the spreadsheet, fixing said errors, hence the most accurate file will be the one in root directory: `spreadsheet.csv`, a csv file generated from the information on [my spreadsheet](https://docs.google.com/spreadsheets/d/12htSAMg67czl8cpkj1mX0TuAFvqL_PJLI4hv1arG5-M/edit#gid=1451660661). `spreadsheet.csv` removes any albums that I added manually, by relation, or on a recommendation. 

You can also use [`SQL/statements.sql`](https://github.com/seanbreckenridge/albums/tree/master/SQL) to create a MySQL schema with similar data to `spreadsheet.csv`. These files will be updated whenever I add something to the list.

##### Sources for `spreadsheet.csv`:

* [1001 Albums You Must Hear Before You Die](https://en.wikipedia.org/wiki/1001_Albums_You_Must_Hear_Before_You_Die). I attempted to include any albums that have ever been in the book, multiple versions with different lineups have come out in 2005, 2008, 2010, 2011, and 2016.

* [Rolling Stone's 500 Greatest Albums of All Time](https://en.wikipedia.org/wiki/Rolling_Stone%27s_500_Greatest_Albums_of_All_Time). Likewise, the count here is 516, due to multiple versions.

* Wins from the four big [AMA](https://en.wikipedia.org/wiki/American_Music_Award) Categories relating to albums:
    * [Favorite Pop/Rock Album](https://en.wikipedia.org/wiki/American_Music_Award_for_Favorite_Pop/Rock_Album)
    * [Favorite Soul/R&B Album](https://en.wikipedia.org/wiki/American_Music_Award_for_Favorite_Soul/R%26B_Album)
    * [Favorite Country Album](https://en.wikipedia.org/wiki/American_Music_Award_for_Favorite_Country_Album)
    * [Favorite Rap/Hip-Hop Album](https://en.wikipedia.org/wiki/American_Music_Award_for_Favorite_Rap/Hip-Hop_Album)

* Wins from a multitude (though not all) Grammy Awards, listed [here](https://github.com/seanbrecke/albums/tree/master/src/Grammy).

Both the [AMA](https://github.com/seanbrecke/albums/tree/master/src/AMA) and [Grammy](https://github.com/seanbrecke/albums/tree/master/src/Grammy) directories have an `all.csv` (nominations and wins) and `wins.csv` (just wins) file.

##### `nextalbums.py`

A `python3.6` script used to interact with the sheets document and maintain `spreadsheets.csv`.

Help:

```
usage: python3 nextalbums.py [-h] [-c COUNT] [-r] [-o] [-q] [--csv]

List the Next Albums to listen to.

optional arguments:
  -h, --help               show this help message and exit
  -c COUNT, --count COUNT  Changes the number of albums to return. Default is
                           10.
  -r, --random             Chooses random albums instead of listing
                           chronologically.
  -o, --open               Open the cell that corresponds to the next album in
                           the spreadsheet online. Ignored if choosing
                           randomly.
  -q, --quiet              quiet mode - only print errors.
  --csv                    Generates a CSV file without any scores/'listened
                           on' dates.
```

###### Examples:

Return the next 7 albums to listen to (chronologically), and open the cell that corresponds to <i>September of My Years</i> in a web browser:
```
$ python3 nextalbums.py -oc 7
+----------------------------+----------------+------+
| Album                      | Artist         | Year |
+----------------------------+----------------+------+
| September of My Years      | Frank Sinatra  | 1966 |
| The In Crowd               | Ramsey Lewis   | 1966 |
| The Return of Roger Miller | Roger Miller   | 1966 |
| A Man and His Music        | Frank Sinatra  | 1967 |
| Don't Come Home A-Drinkin' | Loretta Lynn   | 1967 |
| Goin' Out of My Head       | Wes Montgomery | 1967 |
| Caetano Veloso             | Caetano Veloso | 1968 |
+----------------------------+----------------+------+
```
Don't print anything and open the cell that corresponds to the next album to listen to in a web browser.
```
$ python3 nextalbums.py -qo
```

Dependencies: `pip3 install --user --upgrade google-api-python-client prettytable oauth2client discogs_client termcolor`

If you want to run the python files on your own system, you'd have to change the `spreadsheet_id` [here](https://github.com/seanbreckenridge/albums/blob/master/SQL/create_statements.py#L23), [here](https://github.com/seanbreckenridge/albums/blob/master/nextalbums.py#L23), and [here](https://github.com/seanbreckenridge/albums/blob/master/discogs_update.py#L20) to your own copy of the [spreadsheet](https://docs.google.com/spreadsheets/d/12htSAMg67czl8cpkj1mX0TuAFvqL_PJLI4hv1arG5-M/edit#gid=1451660661) (you can create a spreadsheet on your own google account and ⌘A→ ⌘C→⌘V all of it), edit it the [pageId](https://github.com/seanbreckenridge/albums/blob/master/nextalbums.py#L24) (the number after `edit#gid=` when on the google sheets URL), run `setup.py`, and create a file `discogs_token.json` in the root directory (info can be found [here](https://www.discogs.com/developers/)) with contents similar to:

`{"token": "FDJjksdfJkJFDNMoiweiIRWkj", "user_agent": "yourUserNameSecret/1.0"}`

