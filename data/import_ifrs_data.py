#!/usr/bin/env python
from pathlib import Path
from pprint import pprint
import csv
import sqlite3


def create_table(cur, table_name, headers):
    pass

r = Path('archive/utf-8/')

con = sqlite3.connect('ifrs_data.db')
cur = con.cursor()


p = r / Path('손익계산서-연결')
# create tables
headers = []
for f in p.rglob('*.txt'):
    with open(f, encoding='utf-8') as fd:
        data_reader = csv.reader(fd, delimiter='\t')
        for row in data_reader:
            print(f)
            header = ', '.join(row)
            print(header)
            headers.append(header)
            break

# pprint(sorted(headers))
