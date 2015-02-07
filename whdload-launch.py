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
from hashlib import sha1
try:
    import lhafile
except ImportError:
    lha_support = False
else:
    lha_support = True

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

def get_uuid_from_slave(database, slave_name, slave_sha1):
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute("SELECT data,uuid FROM game WHERE data != ''")
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
            if slave_name in name:
                checksum = item.get('sha1')
                if checksum == slave_sha1:
                    uuid = str(UUID(hexlify(fetched[1]).decode()))
                    break
    cursor.close()
    conn.close()
    return uuid

def game_was_scanned(launcher_database, uuid):
    conn = sqlite3.connect(launcher_database)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM game_variant WHERE uuid=? AND have=4", (uuid,))
    variant_name = cursor.fetchone()
    cursor.close()
    conn.close()
    if variant_name:
        print('Found variant: {0}'.format(variant_name[0]))
        return True
    else:
        return False


# main starts here
try:
    cmdlinearg = sys.argv[1]
except IndexError:
    errorquit('Usage: {0} whdloadgame.zip/.lha'.format(sys.argv[0]))

if not os.path.isfile(cmdlinearg):
    errorquit('File not found: {0}'.format(cmdlinearg))

if cmdlinearg.lower().endswith('.zip'):
    try:
        whdlarc = zipfile.ZipFile(cmdlinearg)
    except zipfile.BadZipFile:
        errorquit('Not a valid ZIP file: {0}'.format(cmdlinearg))
elif cmdlinearg.lower().endswith('.lha') and lha_support is True:
    try:
        whdlarc = lhafile.LhaFile(cmdlinearg)
    except lhafile.BadLhaFile:
        errorquit('Not a valid LHA file: {0}'.format(cmdlinearg))
else:
    errorquit('Unknown file type: {0}'.format(cmdlinearg))

slave_name = None
for f in whdlarc.namelist():
    if f.lower().endswith('.slave') and \
        whdlarc.infolist()[whdlarc.namelist().index(f)].file_size < 1000000:
            slave_name = os.path.basename(f)
            slave_sha1 = sha1(whdlarc.read(f)).hexdigest()
            break

if not slave_name:
    errorquit('Could not find whdload slave file.')

print('Found slave: {0} ({1})'.format(slave_name, slave_sha1))

basedir = get_basedir()
if not basedir:
    errorquit('Could not find fs-uae base directory.')

database = os.path.join(basedir, 'Cache', 'oagd.net.sqlite')
if not os.path.isfile(database):
    errorquit('Could not find local oagd.net database.')

uuid = get_uuid_from_slave(database, slave_name, slave_sha1)
if not uuid:
    errorquit('Slave was not found in the database.')

print('Found UUID: {0}'.format(uuid))

launcher_database = os.path.join(basedir, 'Data', 'Database.sqlite')
if not os.path.isfile(launcher_database):
    errorquit('Could not find fs-uae-launcher database.')

if not game_was_scanned(launcher_database, uuid):
    cmdlinearg_dir = os.path.dirname(os.path.realpath(cmdlinearg))
    errorquit('Game was not scanned by fs-uae-launcher.\n\
Please add {0} and rescan your files.'.format(cmdlinearg_dir))

subprocess.call(['fs-uae-launcher', uuid])
