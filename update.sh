#!/usr/bin/env bash
#
# Does upkeep, run discogs_update.py before running this.
# Not including that here to due to its update threshold,
# it may need to be called multiple times before its finished updating

echo "Reminder: Run discogs_update.py and sort the spreadsheet online by Year, then Album Name"
cd $(dirname "$0")
echo "Generating csv..."
python3 generate_csv.py
echo "Creating SQL statements..."
cd SQL
python3 create_statements.py
python3 create_statements.py --use-scores
echo "updating albums..."
cat statements.sql | sudo mysql
echo "updating scorealbums..."
cat score_statements.sql | sudo mysql
cd ../src
echo "Updating src csv files..."
python3 _update_from_db.py
