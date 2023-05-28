#!/usr/bin/env python
import unittest
from collections import defaultdict
from datetime import date, datetime

import pandas as pd
from pathlib import Path
import sqlite3
from tqdm import tqdm

root = Path('archive/utf-8/')

pd.options.display.float_format = '{:,.0f}'.format

conn = sqlite3.connect('../db/CorpMagnifier.db')
cur = conn.cursor()


def csv_error_handler(bad_line: list[str]) -> list[str] | None:
    print(bad_line)
    return None


dtypes_number = [
    '당기',
    '당기 1분기',
    '당기 1분기 3개월',
    '당기 1분기 누적',
    '당기 1분기말',
    '당기 3분기',
    '당기 3분기 3개월',
    '당기 3분기 누적',
    '당기 3분기말',
    '당기 반기',
    '당기 반기 3개월',
    '당기 반기 누적',
    '당기 반기말',
    '전기',
    '전기 1분기',
    '전기 1분기 3개월',
    '전기 1분기 누적',
    '전기 3분기',
    '전기 3분기 3개월',
    '전기 3분기 누적',
    '전기 반기',
    '전기 반기 3개월',
    '전기 반기 누적',
    '전기말',
    '전전기',
    '전전기말',
]

dtypes_date = [
    '결산월', '결산기준일'
]

dtypes_str = [
    '종목코드', '회사명',
]

dtypes_type = dict.fromkeys(dtypes_str, str)


# dtypes_type.update(dict.fromkeys(dtypes_number, int))

def int_converter(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        print(f'"{value}" cannot be converted to float')


converters = dict.fromkeys(dtypes_number, int_converter)


def delete_all_records(cur: sqlite3.Cursor):
    cur.execute('delete from StockCode;')
    cur.execute('delete from ReportItem;')
    cur.execute('delete from ReportType;')
    cur.execute('delete from Report;')
    cur.execute('delete from Corporation;')
    cur.execute('delete from Sector;')
    cur.execute('delete from Market;')
    conn.commit()


def insert_stock_records(cur: sqlite3.Cursor, df: pd.DataFrame):
    result = {
        'Market': 0,
        'Sector': 0,
    }

    # Market
    df_filter = df[['시장구분']].drop_duplicates()
    record_data = [(None, d[0], '') for d in df_filter.to_records(index=False)]
    n = len(record_data)
    # record_data = list(zip(n * [None], data, n * [""]))
    try:
        res = cur.executemany('INSERT INTO Market VALUES (?, ?, ?)', record_data)
        conn.commit()
        result['Market'] = res.rowcount
    except sqlite3.IntegrityError as e:
        # UNIQUE contraint 에 걸리면 OK
        if 'UNIQUE' in e.args[0]:
            pass
        else:
            raise e

    # Sector
    df_filter = df[['업종', '업종명']].drop_duplicates()
    for r in df_filter.to_records(index=False):
        try:
            res = cur.execute('INSERT INTO Sector VALUES (?, ?, ?)', (None, int(r[0]), r[1]))
            result['Sector'] = res.rowcount
        except sqlite3.IntegrityError as e:
            # UNIQUE contraint 에 걸리면 OK
            if 'UNIQUE' in e.args:
                pass
            else:
                raise e
    conn.commit()

    # ReportType, subtype
    df_filter = df[['재무제표종류']].drop_duplicates()
    for r in df_filter.to_records(index=False):
        try:
            res = cur.execute('INSERT INTO ReportType VALUES (?, ?, ?)', (None, r[0], ''))
            result['ReportType'] = res.rowcount
        except sqlite3.IntegrityError as e:
            # UNIQUE contraint 에 걸리면 OK
            if 'UNIQUE' in e.args:
                continue
            else:
                raise e
    conn.commit()

    # Corporation, StockCode,
    df_filter = df[['회사명', '시장구분', '종목코드', '업종']].drop_duplicates()
    for r in df_filter.to_records(index=False):
        corp_name = str(r[0]).strip()
        stock_code = str(r[2]).strip()[1:-1]
        market_pk = cur.execute('SELECT id from Market WHERE name=?', (r[1],)).fetchone()[0]
        sector_pk = cur.execute('SELECT id from Sector WHERE code=?', (int(r[3]),)).fetchone()[0]
        cur.execute('INSERT INTO Corporation VALUES (?, ?, ?, ?)', (None, corp_name, sector_pk, ''))
        conn.commit()
        corp_pk = \
        cur.execute('SELECT id from Corporation WHERE name=? AND sector=?', (corp_name, sector_pk)).fetchone()[0]
        cur.execute('INSERT INTO StockCode VALUES (?, ?, ?, ?, ?)', (None, market_pk, stock_code, corp_pk, ''))
    conn.commit()

    # Corporation
    return result


def get_report(cur:sqlite3.Cursor, report_quarter, report_year, corp_pk, report_type_pk, report_date):
    res = cur.execute('SELECT id from Report WHERE quarter=? AND year=? AND corporation=? AND report_type=? AND date=?',
                      (report_quarter, report_year, corp_pk, report_type_pk, report_date))
    record = res.fetchone()
    if record:
        return record[0]

    return None


def insert_one_record(cur, row):
    pass


def insert_records(cur: sqlite3.Cursor, df: pd.DataFrame, year):
    pbar = tqdm(desc='Importing', total=df.shape[0])
    for idx, row in df.iterrows():
        # market_pk = cur.execute('SELECT id from Market WHERE name=?', (str(row[3]).strip(),)).fetchone()[0]
        report_type_pk = cur.execute('select id from ReportType where name=?', (str(row[0]).strip(),)).fetchone()[0]

        # Report
        report_date = row[7]
        report_year = year
        report_quarter = row[8]
        corp_pk = cur.execute('SELECT id from Corporation WHERE name=?', (row[2],)).fetchone()[0]
        report_pk = get_report(cur, report_quarter, report_year, corp_pk, report_type_pk, report_date)
        if not report_pk:
            cur.execute('INSERT INTO Report VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (None, report_quarter, report_year, '', corp_pk, report_type_pk, report_date))
            conn.commit()
            report_pk = get_report(cur, report_quarter, report_year, corp_pk, report_type_pk, report_date)
            if not report_pk:
                raise sqlite3.OperationalError(f'Cannot find report')

        # ReportItem
        reportitem_amount = row[12]
        reportitem_account_name = row[11]
        reportitem_account_code = row[10]
        reportitem_currency = row[9]
        cur.execute('INSERT INTO ReportItem VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (None, reportitem_currency, reportitem_account_code, reportitem_account_name, reportitem_amount, '', report_pk))
        conn.commit()
        pbar.update(1)


def import_document(f):
    common_columns = ['재무제표종류', '종목코드', '회사명', '시장구분', '업종', '업종명', '결산월', '결산기준일', '보고서종류', '통화', '항목코드', '항목명', '당기']

    # Market
    #   '시장구분'
    # Company
    #   '회사명', '업종', '업종명',
    #   '시장종류에 따라 종목코드가 두개 일수도 있다'
    # StockCode
    #   Market, Company, Code
    # Report
    #   '결산월', '결산기준일', '보고서종류': 1분기보고서, ...
    # ReportType
    #   '재무제표종류' : 현금흐름표, 손익계산서, ...
    # ReportItem
    #   '통화', '항목코드', '항목명', '당기'

    valid_column_indices = range(len(common_columns))
    df = pd.read_csv(f, sep='\t', thousands=',', engine="python", dtype=dtypes_type, usecols=valid_column_indices)
    df.columns = common_columns

    # headers = ','.join(list(df.columns))
    # print(headers)

    # invalid_columns = [c for c in df.columns if 'unnamed' in c.lower()]
    # if len(invalid_columns) > 0:
    #     df = df.drop(labels=invalid_columns, axis=1)
    #
    # for c in df.columns:
    #     if c not in common_columns:
    #         value_columns.add(c)
    # print(df.columns)
    return df


r = root / Path('현금흐름표')
# r = root / Path('포괄손익계산서')
# r = root
value_columns = set()

filelist = list(r.rglob('*.txt'))

delete_all_records(cur)

prev_parent = None
for f in filelist:
    # df = pd.read_csv(f, sep='\t', thousands=',', engine="python", on_bad_lines=csv_error_handler)
    # df = pd.read_csv(f, sep='\t', thousands=',', engine="python", dtype=dtypes_type, converters=converters)
    if prev_parent != f.parent:
        prev_parent = f.parent
        print(f.parent)
    print(f)

    year = int(f.name[:4])

    df = import_document(f)
    res = insert_stock_records(cur, df)
    res = insert_records(cur, df, year)

# pd.set_option('display.max_rows', None)
# pd.set_option('display.max_columns', None)
# pd.set_option('display.width', None)
# pd.set_option('display.max_colwidth', -1)

if len(value_columns) > 0:
    print(value_columns)


class Test(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.f = filelist[1]

    @unittest.skip("")
    def test_multiple_loading(self):
        prev_parent = None
        for f in filelist:
            # df = pd.read_csv(f, sep='\t', thousands=',', engine="python", on_bad_lines=csv_error_handler)
            # df = pd.read_csv(f, sep='\t', thousands=',', engine="python", dtype=dtypes_type, converters=converters)
            if prev_parent != f.parent:
                prev_parent = f.parent
                print(f.parent)

            print(f)
            df = import_document(f)

    @unittest.skip("")
    def test_valid_df(self):
        df = import_document(self.f)
        for c in df.columns:
            l = list(df[c].unique())
            print(80 * '-')
            print(c)
            for d in l:
                print(d)

    def test_insert_stock(self):
        delete_all_records(cur)
        df = import_document(self.f)
        res = insert_stock_records(cur, df)
        res = insert_records(cur, df)
        self.assertGreater(sum(res.values()), 0)

    def doCleanups(self) -> None:
        super().doCleanups()
        conn.close()
