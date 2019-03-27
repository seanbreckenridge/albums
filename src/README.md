This directory houses csv files generated from the SQL database, for each reason an album is on the list.

If an album has multiple reasons for being on the spreadsheet, its listed in multiple files.

This uses the script `_update_from_db.py` to generate the csv files, with credentials for the database (MySQL server on your system) stored in `_sql_cred.yaml` with contents similar to:

```
user: usernamehere
passwd: passwordhere
```

Run: `python3 _update_from_db.py`