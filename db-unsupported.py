#!/usr/bin/env python3

import hashlib
import os
import sys
import sqlite3
import json
import zlib
import subprocess
from multiprocessing import Pool


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


def get_floppy_list(gamedir):
    sys.stderr.write('Checksumming your floppy images...\n')
    floppy_list = []
    fexts = ('.adf', '.ipf')
    for root, folders, files in os.walk(gamedir):
        for file in files:
            if file.lower().endswith(fexts):
                file_with_path = os.path.join(root, file)
                with open(file_with_path, 'rb') as f:
                    data = f.read()
                floppy_list.append((file_with_path, hashlib.sha1(
                    data).hexdigest()))
    sys.stderr.write('Done checksumming {0} floppy images.\n'.format(
        len(floppy_list)))
    return floppy_list


def get_db_checksums(db):
    sys.stderr.write('Searching for floppy images in OAGD...\n')
    db_checksums = set()
    fexts = ('.adf', '.ipf', '.dms')
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute("SELECT data FROM game WHERE data !=''")
    while True:
        fetched = cursor.fetchone()
        if not fetched:
            break
        data = json.loads(zlib.decompress(fetched[0]).decode())
        json_file_list = data.get('file_list')
        if not json_file_list:
            continue
        file_list = json.loads(json_file_list)
        for file in file_list:
            if file['name'].lower().endswith(fexts):
                db_checksums.add(file['sha1'])
    conn.close()
    sys.stderr.write('Got checksums for {0} unique floppyimages from OAGD.\n'
                     .format(len(db_checksums)))
    return db_checksums


if __name__ == '__main__':
    try:
        path = sys.argv[1]
    except IndexError:
        sys.stderr.write('Usage: {0} /path/to/gamedir\n'.format(sys.argv[0]))
        quit()
    basedir = get_basedir()
    if not basedir:
        sys.stderr.write('Could not get FS-UAE base directory.\n')
        quit(1)
    db = os.path.join(basedir, 'Cache', 'oagd.net.sqlite')
    with Pool(processes=2) as pool:
        floppy_list_pool = pool.apply_async(get_floppy_list, [path])
        db_checksums_pool = pool.apply_async(get_db_checksums, [db])
        floppy_list = floppy_list_pool.get()
        db_checksums = db_checksums_pool.get()
    for floppy in floppy_list:
        if floppy[1] not in db_checksums:
            sys.stdout.write(floppy[0] + '\n')
