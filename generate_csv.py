import sys
import os
import re
import csv
from itertools import chain

from nextalbums import get_credentials, get_values

def main():
    credentials = get_credentials()
    values = get_values(credentials, "A2:L", "FORMULA")
    csv_fullpath = os.path.join(os.path.dirname(__file__), "spreadsheet.csv")
    values = [row for row in values if not
              set(map(lambda s: s.lower(), re.split("\s*,\s*", row[5])))
              .issubset(set(["manual", "relation", "recommendation"]))]
    with open(csv_fullpath, 'w') as csv_file:
        csv_writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL)
        max_row_len = max(map(len,values))
        for row in values:
            # write '' to empty cells, to make all the row lengths in the csv file the same
            padded = row + [''] * (max_row_len - len(row))
            # remove score and listened on dates
            padded[0] = ""
            padded[4] = ""
            csv_writer.writerow(padded)
        print(f"Wrote to {csv_fullpath} successfully.")

if __name__ == "__main__":
    main()
