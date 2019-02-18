### albums
A collection of csv/sql files containing popular/acclaimed albums, used to make a inordinate list of albums to listen to.

This is a personal project of mine, but I thought I'd leave these files up here in case anyone wanted to use them.

The source csv files are bound to have errors somewhere, e.g. duplicates due to slight differences in album names. I've stopped updating the `wins.csv`/`all.csv` files manually. If you wish to list the wins for a certain award, it would be most accurate to use the SQL files and query for them. [Example](SQL#example-queries)

The 'Year' column refers to date released. However, in source csv files for AMA's and Grammies, the year is often the date awarded.

`python3 discogs_update.py` uses the [Discogs API](https://github.com/discogs/discogs_client) to validate the data in the spreadsheet, fixing said errors, hence the most accurate file will be the one in root directory: `spreadsheet.csv`, a csv file generated from the information on [my spreadsheet](https://docs.google.com/spreadsheets/d/12htSAMg67czl8cpkj1mX0TuAFvqL_PJLI4hv1arG5-M/edit#gid=1451660661). `spreadsheet.csv` removes any albums that I added manually, by relation, or on a recommendation.

You can also use [`SQL/statements.sql`](SQL/) to create a MySQL schema with similar data to `spreadsheet.csv`. These files will be updated whenever I add something to the list.

##### Sources for `spreadsheet.csv`:

* [1001 Albums You Must Hear Before You Die](https://en.wikipedia.org/wiki/1001_Albums_You_Must_Hear_Before_You_Die). I attempted to include any albums that have ever been in the book, multiple versions with different lineups have come out in 2005, 2008, 2010, 2011, and 2016.

* [Rolling Stone's 500 Greatest Albums of All Time](https://en.wikipedia.org/wiki/Rolling_Stone%27s_500_Greatest_Albums_of_All_Time). Likewise, the count here is 516, due to multiple versions.

* Wins from the four big [AMA](https://en.wikipedia.org/wiki/American_Music_Award) Categories relating to albums:
    * [Favorite Pop/Rock Album](https://en.wikipedia.org/wiki/American_Music_Award_for_Favorite_Pop/Rock_Album)
    * [Favorite Soul/R&B Album](https://en.wikipedia.org/wiki/American_Music_Award_for_Favorite_Soul/R%26B_Album)
    * [Favorite Country Album](https://en.wikipedia.org/wiki/American_Music_Award_for_Favorite_Country_Album)
    * [Favorite Rap/Hip-Hop Album](https://en.wikipedia.org/wiki/American_Music_Award_for_Favorite_Rap/Hip-Hop_Album)

* Wins from a multitude (though not all) Grammy Awards, listed [here](src/Grammy).

##### `nextalbums.py`

A `python3` script used to interact with the sheets document and maintain `spreadsheets.csv`.

```
usage: python3 nextalbums.py [-h] [-n N] [-r] [-o] [-q] [-m] [--csv]

List the Next Albums to listen to.

optional arguments:
  -h, --help    show this help message and exit
  -n N          Changes the number of albums to return. Default is 10.
  -r, --random  Chooses random albums instead of listing chronologically.
  -o, --open    Open the cell that corresponds to the next album in the
                spreadsheet online. Ignored if choosing randomly.
  -q, --quiet   quiet mode - only print errors.
  -m, --memory  Open the spreadsheet online based on the previous call to next
                albums and quit. This is much faster since it doesn't require
                an API call(the line stored in '.prev_call')
  --csv         Generates a CSV file without any scores/'listened on' dates.
```

###### Examples:

Return the next 7 albums to listen to (chronologically), and open the cell that corresponds to <i>September of My Years</i> in a web browser:
```
$ python3 nextalbums.py -on 7
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

If you want to run the python files on your own system, you'd have to

1. Change the `spreadsheet_id` [here](https://github.com/seanbreckenridge/albums/blob/master/nextalbums.py#L23) (the id is the long string after `/d/` in the URL when you're editing it) to your own copy of the [spreadsheet](https://docs.google.com/spreadsheets/d/12htSAMg67czl8cpkj1mX0TuAFvqL_PJLI4hv1arG5-M/edit#gid=1451660661) (you can create a spreadsheet on your own google account and ⌘A→ ⌘C→⌘V all of it). 

2. Edit the [pageId](https://github.com/seanbreckenridge/albums/blob/master/nextalbums.py#L24) (the number after `edit#gid=` when on the google sheets URL)

3. Create a file named `client_secret.json` in the root directory which contains your credentials for a google sheets OAuth connection. [Tutorial here](https://console.developers.google.com); download your created credentials from [here](https://console.developers.google.com/apis/credentials)

4. Run `setup.py`

5. (If you want to add albums and validate them with `discogs_update.py`) Create a file `discogs_token.yaml` in the root directory (info can be found [here](https://www.discogs.com/developers/), token [here](https://www.discogs.com/settings/developers)) with contents similar to: 

```
user_agent: myPython3DiscogsClient/1.0
token: !!str FDJjksdfJkJFDNMoiweiIRWkj
```
