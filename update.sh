#!/usr/bin/env bash
#
# Does upkeep, run discogs_update.py before running this.
# Not including that here to due to its update threshold,
# it may need to be called multiple times before its finished updating

echo "Reminder: Run discogs_update.py and sort the spreadsheet online by Year, then Album Name"
cd "$(dirname "$0")" || exit
echo "Generating csv..."
python3 generate_csv.py
echo "Creating SQL statements..."
cd SQL || exit
python3 create_statements.py
python3 create_statements.py --use-scores
echo "updating albums..."
sudo cat statements.sql | sudo mysql
echo "updating scorealbums..."
sudo cat score_statements.sql | sudo mysql
cd ../src || exit
echo "Updating src csv files..."
python3 _update_from_db.py
