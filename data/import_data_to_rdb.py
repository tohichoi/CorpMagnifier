#!/usr/bin/env python
import argparse
import unittest
import pandas as pd
from pathlib import Path
import sqlite3
from tqdm import tqdm
import config

root = Path('archive/utf-8/')

pd.options.display.float_format = '{:,.0f}'.format

# create database with sqlite3
# cd db
# sqlite3 CorpMagnifier.db <create-db.sql

conn = sqlite3.connect('../db/CorpMagnifier.db')
cur = conn.cursor()


def csv_error_handler(bad_line: list[str]) -> list[str] | None:
    print(bad_line)
    return None


def int_converter(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        print(f'"{value}" cannot be converted to float')


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
            if 'UNIQUE' in e.args[0]:
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
            if 'UNIQUE' in e.args[0]:
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

        try:
            cur.execute('INSERT INTO StockCode VALUES (?, ?, ?, ?, ?)', (None, market_pk, stock_code, corp_pk, ''))
            conn.commit()
        except sqlite3.IntegrityError as e:
            # UNIQUE contraint 에 걸리면 OK
            if 'UNIQUE' in e.args[0]:
                pass
            else:
                raise e

    # Corporation
    return result


def get_report(cur: sqlite3.Cursor, report_quarter, report_year, corp_pk, report_type_pk, report_date):
    res = cur.execute('SELECT id from Report WHERE quarter=? AND year=? AND corporation=? AND report_type=? AND date=?',
                      (report_quarter, report_year, corp_pk, report_type_pk, report_date))
    record = res.fetchone()
    if record:
        return record[0]

    return None


def insert_records(cur: sqlite3.Cursor, df: pd.DataFrame, year):
    pbar = tqdm(desc='Importing', total=df.shape[0])
    for idx, row in df.iterrows():
        corp_name = str(row[2].strip())
        report_type = str(row[0]).strip()
        # market_pk = cur.execute('SELECT id from Market WHERE name=?', (str(row[3]).strip(),)).fetchone()[0]
        report_type_pk = cur.execute('select id from ReportType where name=?', (report_type,)).fetchone()[0]

        # Report
        report_date = str(row[7]).strip()
        report_year = year
        report_quarter = str(row[8]).strip()
        r = cur.execute('SELECT id from Corporation WHERE name=?', (corp_name,))
        if r:
            rr = r.fetchone()
            if not rr:
                raise Exception(f'Cannot find corp: {corp_name}')
            corp_pk = rr[0]
        else:
            raise Exception(f'Cannot find corp: {corp_name}')
        report_pk = get_report(cur, report_quarter, report_year, corp_pk, report_type_pk, report_date)
        if not report_pk:
            cur.execute('INSERT INTO Report VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (None, report_quarter, report_year, '', corp_pk, report_type_pk, report_date))
            conn.commit()
            report_pk = get_report(cur, report_quarter, report_year, corp_pk, report_type_pk, report_date)
            if not report_pk:
                raise sqlite3.OperationalError(f'Cannot find report')

        # ReportItem
        reportitem_amount = str(row[12]).strip()
        reportitem_account_name = str(row[11]).strip()
        reportitem_account_code = str(row[10]).strip()
        reportitem_currency = str(row[9]).strip()
        cur.execute('INSERT INTO ReportItem VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (None, reportitem_currency, reportitem_account_code, reportitem_account_name, reportitem_amount, '',
                     report_pk))
        conn.commit()
        pbar.update(1)


def import_document(f):
    common_columns = ['재무제표종류', '종목코드', '회사명', '시장구분', '업종', '업종명', '결산월', '결산기준일', '보고서종류', '통화', '항목코드', '항목명', '당기']
    dtypes_str = [
        '종목코드', '회사명',
    ]

    dtypes_type = dict.fromkeys(dtypes_str, str)

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

    return df


if __name__ == '__main__':
    data_dirs = [
        '포괄손익계산서',
        '포괄손익계산서-연결',
        '현금흐름표',
        '현금흐름표-연결',
        '손익계산서',
        '손익계산서-연결',
        # '자본변동표',
        # '자본변동표-연결',
        '재무상태표',
        '재무상태표-연결',
    ]

    parser = argparse.ArgumentParser(description='Corporation Magnifier')
    parser.add_argument('--delete-all-records', '-D', help='Delete all records',
                        action='store_true', required=False)
    args = parser.parse_args()

    if args.delete_all_records:
        ans = input('Delete all records? (y/n)')
        if ans.lower() == 'y':
            delete_all_records(cur)
        else:
            print('Not deleted')

    for dd in data_dirs:
        r = root / Path(dd)

        filelist = list(r.rglob('*.txt'))

        prev_parent = None
        for f in filelist:
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

    # if len(value_columns) > 0:
    #     print(value_columns)


class Test(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()

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
        self.f = filelist[1]
        df = import_document(self.f)
        for c in df.columns:
            l = list(df[c].unique())
            print(80 * '-')
            print(c)
            for d in l:
                print(d)

    def test_insert_stock(self):
        delete_all_records(cur)
        # self.f = filelist[1]
        # fn = Path('2017_반기보고서_01_재무상태표_20230301.txt')
        fn = Path('2017_사업보고서_05_자본변동표_연결_20230524.txt')
        self.f = root / Path('자본변동표-연결') / fn
        year = int(fn.name[:4])
        df = import_document(self.f)
        res = insert_stock_records(cur, df)
        res = insert_records(cur, df, year)
        self.assertGreater(sum(res.values()), 0)

    def doCleanups(self) -> None:
        super().doCleanups()
        conn.close()
