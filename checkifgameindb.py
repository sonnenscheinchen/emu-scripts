#!/usr/bin/env python3

import sys
import os
import hashlib
import sqlite3
import zlib

# change me!
db = '~/FS-UAE/Data/Game Database.sqlite'

#change me!
tosecdat = (
    '~/FS-UAE/tosecdat/Commodore Amiga - Games - Public Domain - [ADF] (TOSEC-v2013-09-29_CM).dat',
    '~/FS-UAE/tosecdat/Commodore Amiga - Games - SPS (TOSEC-v2013-09-29_CM).dat',
    '~/FS-UAE/tosecdat/Commodore Amiga - Games - [ADF] (TOSEC-v2013-09-29_CM).dat'
)

try:
    gamedir = sys.argv[1]
except IndexError:
    print('usage: {0} /path/to/gamedir [-v]'.format(sys.argv[0]))
    quit()

games = []
fexts = ('.adf', '.ipf')

for root, folders, files in os.walk(gamedir):
    for file in files:
        if file.lower().endswith(fexts):
            games.append(os.path.join(root, file))

if not games:
    print('no disk images to check for')
    quit()

conn = sqlite3.connect(os.path.expanduser(db))


def do_hash(game):
    with open(game, 'rb') as f:
        data = f.read()
    return hashlib.sha1(data).hexdigest()


def game_in_db(sha1sum):
    cursor = conn.cursor()
    cursor.execute("SELECT data FROM game")
    while True:
        fetched = cursor.fetchone()
        if not fetched:
            break
        data = zlib.decompress(fetched[0])
        if sha1sum in data.decode():
            cursor.close()
            return 'yes'
    cursor.close()
    return ''


def game_in_tosec(sha1sum):
    for dat in tosecdat:
        with open(os.path.expanduser(dat)) as f:
            for line in f:
                if sha1sum in line:
                    return line.split(sep='\"')[1]
    return ''

maxlen = len(max(games, key=len)) + 3

if '-v' in sys.argv:
    print('Image Name'.ljust(maxlen),  'in_oagd'.ljust(8), 'in_TOSEC'.ljust(8))
else:
    print('sha1sum'.ljust(41), 'TOSEC name')

toseccount = 0
dbcount = 0

for game in games:
    sha1sum = do_hash(game)
    indb = game_in_db(sha1sum)
    intosec = game_in_tosec(sha1sum)
    if indb:
        dbcount += 1
    if intosec:
        toseccount += 1
    if '-v' in sys.argv:
        print(game.ljust(maxlen), indb.center(8), intosec.ljust(8))
    else:
        if not indb and intosec:
            #print('{0}, {1}, {2}'.format(os.path.basename(game), sha1sum, intosec))
            print('{0}, {1}'.format(sha1sum, intosec))

conn.close()

print('images total: {0}, in db: {1}, in tosec: {2}'.format(len(games), dbcount, toseccount))
