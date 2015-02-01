#!/usr/bin/env python3

import sqlite3
from binascii import hexlify
import zlib
import sys
import os
from shutil import copyfile

try:
    in_db = sys.argv[1]
except IndexError:
    print('Usage: {0} /path/to/oagd.net..sqlite'.format(sys.argv[0]))
    quit()

out_db = os.path.join(os.path.dirname(
    in_db), 'oagd.net-uncompressed.sqlite')

copyfile(in_db, out_db)
conn = sqlite3.connect(out_db)
cursor = conn.cursor()
cursor2 = conn.cursor()
cursor.execute('SELECT id,uuid,data FROM game')
while True:
    fetched = cursor.fetchone()
    if not fetched:
        break
    idx = fetched[0]
    mb = hexlify(fetched[1]).decode()
    uuid = '{0}-{1}-{2}-{3}-{4}'.format(
        mb[:8], mb[8:12], mb[12:16], mb[16:20], mb[20:])
    data = zlib.decompress(fetched[2])
    cursor2.execute(
        'UPDATE game SET uuid = ?, data = ? WHERE id = ?', (uuid, data, idx))

conn.commit()
cursor.close()
cursor2.close()
conn.close()