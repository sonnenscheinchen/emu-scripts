#!/usr/bin/env python3

import sys
import os
import json
import sqlite3
from binascii import unhexlify
import zlib
import subprocess
import pdb


def get_basedir():
    if os.path.isdir(str(os.environ.get('FS_UAE_BASE_DIR'))):
        return os.environ['FS_UAE_BASE_DIR']
    basedirconf = os.path.expanduser('~/.config/fs-uae/base-dir')
    if os.path.isfile(basedirconf):
        with open(basedirconf) as f:
            path = f.readline().strip()
        if os.path.isdir(path):
            return path
    basedirconf = os.path.expanduser('~/.config/fs-uae/fs-uae.conf')
    if os.path.isfile(basedirconf):
        with open(basedirconf) as f:
            for line in f:
                if line.split('=')[0].strip() == 'base_dir':
                    path = line.split('=')[1].strip()
                    if os.path.isdir(path):
                        return path
    try:
        docdir = subprocess.check_output(
            ['xdg-user-dir', 'DOCUMENTS']).decode().strip(os.linesep)
        path = os.path.join(docdir, 'FS-UAE')
        if os.path.isdir(path):
            return path
    except:
        path = os.path.join(os.path.expanduser('~/FS-UAE'))
        if os.path.isdir(path):
            return path
    return None


def get_config_from_game_id(game_id):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute("SELECT data FROM game WHERE id = ?", (game_id,))
    data = zlib.decompress(cursor.fetchone()[0])
    doc = json.loads(data.decode())
    next_parent_uuid = doc.get("parent_uuid", "")
    while next_parent_uuid:
        cursor.execute(
            "SELECT data FROM game WHERE uuid = ?",
            (sqlite3.Binary(
                unhexlify(next_parent_uuid.replace("-", ""))),))
        data = zlib.decompress(cursor.fetchone()[0])
        next_doc = json.loads(data.decode())
        next_parent_uuid = next_doc.get("parent_uuid", "")
        next_doc.update(doc)
        doc = next_doc
    cursor.close()
    conn.close()
    return doc


def get_gamelist_from_searchstring(searchstring, fileplatform):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute("SELECT data,id FROM game WHERE data != ''")
    gamelist = []
    while True:
        fetched = cursor.fetchone()
        if not fetched:
            break
        data = zlib.decompress(fetched[0])
        game_id = fetched[1]
        doc = json.loads(data.decode())
        gamename = doc.get('game_name', '')
        platform = doc.get('platform', '')
        if searchstring in gamename.lower() and platform in fileplatform:
            gamelist.append((game_id, gamename, platform))
    cursor.close()
    conn.close()
    return gamelist


floppylist = sys.argv[1:]
if not floppylist:
    print('{0} - manually add games to fs-uae launcher'.format(
        sys.argv[0]))
    print('Usage: {0} <diskimages>'.format(sys.argv[0]))
    quit()

for file in floppylist:
    if not os.path.isfile(file):
        sys.stderr.write(
            'Can\'t add non-existant file to config: {0}\n'.format(file))
        quit(1)

#get platform by file extension
floppyexts = ('.adf', '.ipf', '.adz', '.dms')
cdexts = ('.iso', '.cue')
if floppylist[0].lower().endswith(floppyexts):
    fileplatform = 'Amiga'
elif floppylist[0].lower().endswith(cdexts):
    fileplatform = 'CD32i, CDTV'
else:
    fileplatform = 'Amiga, CD32, CDTV'

basedir = get_basedir()
if not basedir:
    sys.stderr.write('Could not find fs-uae base dir.\n')
    quit(1)

global db
db = os.path.join(basedir, 'Cache', 'oagd.net.sqlite')
if not os.path.isfile(db):
    sys.stderr.write('Could not find local game database.\n')
    quit(1)

print('Searching games for platform(s): {0}'.format(fileplatform))

searchstring = input('\nPlease enter the name of the game.: >> ').lower()

if len(searchstring) < 4:
    sys.stderr.write(
        'Sorry, the search term must contain at least 4 characters.\n')
    quit(1)

gamelist = get_gamelist_from_searchstring(searchstring, fileplatform)

if not gamelist:
    print('{0} was not found in the database.'.format(searchstring))
    quit()

print('')
for game in enumerate(gamelist):
    print('{0} - {1} [{2}]'.format(game[0], game[1][1], game[1][2]))

gameno = input('Please select a game from the list: >> ')
if not gameno.isdigit() or 0 < int(gameno) > len(gamelist) - 1:
    quit()

gameconfig = get_config_from_game_id(gamelist[int(gameno)][0])

configname = '{0} [custom].fs-uae'.format(gameconfig.get('game_name'))
configfullname = os.path.join(basedir, 'Configurations', configname)
with open(configfullname, 'wt') as fsuaeconf:
    fsuaeconf.write('[fs-uae]\n')
    for option in gameconfig:
        if not option.startswith('__') or not option.startswith('platform'):
            fsuaeconf.write('{0} = {1}\n'.format(
                option, gameconfig[option]))
    if gameconfig.get('platform') == 'Amiga':
        [fsuaeconf.write('floppy_drive_{0} = {1}\n'.format(
            floppyno, floppy)) for floppyno, floppy in zip(range(4), floppylist)]
        [fsuaeconf.write('floppy_image_{0} = {1}\n'.format(
            floppyimageno, floppyimagefile)) for floppyimageno, floppyimagefile in zip(
                range(20), floppylist)]
        if '[AGA]' in gameconfig.get('game_name'):
            fsuaeconf.write('amiga_model = A1200\n')
    elif gameconfig.get('platform') == 'CD32':
        fsuaeconf.write('cdrom_drive_0 = {0}\n'.format(floppylist[0]))
        fsuaeconf.write('amiga_model = CD32\n')
    elif gameconfig.get('platform') == 'CDTV':
        fsuaeconf.write('cdrom_drive_0 = {0}\n'.format(floppylist[0]))
        fsuaeconf.write('amiga_model = CDTV\n')
    else:
        #here be dragons
        pass

print('\nWrote config to')
print(configfullname)
print('Don\'t forget to setup an appropriate Amiga configuration!')


#pdb.set_trace()
