#!/usr/bin/python3

import sys
import os
import zipfile
import sqlite3
import subprocess
from binascii import hexlify
from uuid import UUID
from zlib import decompress
from json import loads

def stderrprint(text):
    sys.stderr.write('{0}\n'.format(text))

def errorquit(text):
    stderrprint(text)
    quit(1)

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

def get_uuid_from_slave(database, slave_name):
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute("SELECT data,uuid FROM game")
    uuid = None
    while uuid is None:
        fetched = cursor.fetchone()
        if not fetched:
            break
        data = decompress(fetched[0])
        doc = loads(data.decode())
        file_list = doc.get('file_list')
        if not file_list:
            continue
        for item  in loads(file_list):
            name = item.get('name')
            if not name:
                continue
            if slave_name in name:
                uuid = UUID(hexlify(fetched[1]).decode())
                break
    cursor.close()
    conn.close()
    return str(uuid)


# main starts here
try:
    cmdlinearg = sys.argv[1]
except IndexError:
    errorquit('Usage: {0} whdloadgame.zip'.format(sys.argv[0]))

try:
    whdlzip = zipfile.ZipFile(cmdlinearg)
except zipfile.BadZipFile:
    errorquit('Not a valid ZIP file: {0}'.format(cmdlinearg))
except FileNotFoundError:
    errorquit('File not found: {0}'.format(cmdlinearg))

slave_name = None
for f in whdlzip.namelist():
    if f.lower().endswith('.slave'):
        slave_name = os.path.basename(f)
        break

if not slave_name:
    errorquit('Could not find whdload slave file.')

print('Found slave: {0}'.format(slave_name))

basedir = get_basedir()
if not basedir:
    errorquit('Could not find fs-uae base directory.')

database = os.path.join(basedir, 'Cache', 'oagd.net.sqlite')
if not os.path.isfile(database):
    errorquit('Could not find game database.')

uuid = get_uuid_from_slave(database, slave_name)
if not uuid:
    errorquit('{0} was not found in the database.'.format(slave_name))

print(' Found UUID: {0}'.format(uuid))
subprocess.call(['fs-uae-launcher', uuid])
