#!/usr/bin/env python3

import sys
import os
import sqlite3
import json
import argparse

parser = argparse.ArgumentParser(description='Ask the oagdb.')
parser.add_argument('--keys', help='get all keys in db', action="store_true")
parser.add_argument('--unique', help='get unique values for a key', metavar='KEY')
parser.add_argument('--print', help='print value of KEY2 if KEY1 exists', nargs=2, metavar=('KEY1', 'KEY2'))
parser.add_argument('--search', help='if KEY1 has VALUE print value of KEY2', nargs=3, metavar=('KEY1', 'VALUE', 'KEY2'))

args = parser.parse_args()

db = '~/FS-UAE/Cache/oagd.net.sqlite'

conn = sqlite3.connect(os.path.expanduser(db))
c = conn.cursor()
c.execute('select data from game')
res = set()

while True:
    fetched = c.fetchone()
    if not fetched:
        break
    doc = json.loads(fetched[0].decode())
    if args.keys:
        for key in doc:
            res.add(key)
    elif args.unique:
        res.add(doc.get(args.unique))
    elif args.print:
        if doc.get(args.print[0], ''):
            res.add(doc.get(args.print[1]))
    elif args.search:
        if args.search[1] in doc.get(args.search[0], ''):
            res.add(doc.get(args.search[2]))

for item in res:
    print(item)

c.close()
conn.close()
