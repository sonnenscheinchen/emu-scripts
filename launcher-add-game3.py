#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt4 import QtCore, QtGui
import sys
import os
import json
import sqlite3
from binascii import unhexlify
import zlib
import subprocess
import threading
#import pdb
import queue


class Ui_LauncherAdd(object):
    
    def __init__(self):
        self.basedir = get_basedir()
        if not self.basedir:
            QtGui.QMessageBox.critical(
                None, 'Error', 'Could not find fs-uae base dir.', QtGui.QMessageBox.Ok)
            quit(1)

        self.db = os.path.join(self.basedir, 'Cache', 'oagd.net.sqlite')
        if not os.path.isfile(self.db):
            QtGui.QMessageBox.critical(
                None, 'Error', 'Could not find local game database.', QtGui.QMessageBox.Ok)
            quit(1)
        
        worker = SearchGameList(self.db)
        worker.setDaemon(True)
        worker.start()

    def setupUi(self, LauncherAdd):
        LauncherAdd.resize(380, 240)
        self.horizontalLayout = QtGui.QHBoxLayout(LauncherAdd)
        self.frame = QtGui.QFrame(LauncherAdd)
        self.frame.setFrameShape(QtGui.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtGui.QFrame.Raised)
        self.gridLayout = QtGui.QGridLayout(self.frame)
        self.lineEditSearchFor = QtGui.QLineEdit(self.frame)
        self.gridLayout.addWidget(self.lineEditSearchFor, 0, 1, 1, 2)
        self.labelSearchFor = QtGui.QLabel(self.frame)
        self.gridLayout.addWidget(self.labelSearchFor, 0, 0, 1, 1)
        self.pushButtonWriteConfig = QtGui.QPushButton(self.frame)
        self.gridLayout.addWidget(self.pushButtonWriteConfig, 2, 2, 1, 1)
        self.listWidgetResults = QtGui.QListWidget(self.frame)
        self.gridLayout.addWidget(self.listWidgetResults, 1, 0, 1, 3)
        self.horizontalLayout.addWidget(self.frame)

        self.pushButtonWriteConfig.clicked.connect(self.writeconfig)
        self.lineEditSearchFor.returnPressed.connect(self.searchdb)
        self.lineEditSearchFor.textChanged.connect(self.searchdb)

        LauncherAdd.setWindowTitle("Launcher Add")
        self.labelSearchFor.setText("Search for:")
        self.pushButtonWriteConfig.setText("Write Config")

    def searchdb(self):
        self.searchfor = self.lineEditSearchFor.text()
        if len(self.searchfor) < 4:
            self.listWidgetResults.clear()
            return
        SearchGameList.q.put(self.searchfor)
        
    def writeconfig(self):
        SearchGameList.q.join()
        entry = self.listWidgetResults.currentRow()
        #print(entry)
        if entry < 0:
            QtGui.QMessageBox.information(
                None, 'Info', 'Please select a game first.', QtGui.QMessageBox.Ok)
            return
        gameconfig = get_config_from_game_id(SearchGameList.gamelist[entry][0], self.db)
        #print(gameconfig)
        configname = '{0} [custom].fs-uae'.format(gameconfig.get('game_name'))
        configfullname = os.path.join(self.basedir, 'Configurations', configname)
        with open(configfullname, 'wt') as fsuaeconf:
            fsuaeconf.write('[fs-uae]\n')
            for option in gameconfig:
                print(option)
                if not option.startswith('__') and not option == 'platform':
                    print('wrote ' + option)
                    fsuaeconf.write('{0} = {1}\n'.format(
                        option, gameconfig[option]))
            if gameconfig.get('platform') == 'Amiga':
                if '[AGA]' in gameconfig.get('game_name'):
                    fsuaeconf.write('amiga_model = A1200\n')
            elif gameconfig.get('platform') == 'CD32':
                fsuaeconf.write('amiga_model = CD32\n')
            elif gameconfig.get('platform') == 'CDTV':
                fsuaeconf.write('amiga_model = CDTV\n')
            else:
                #here be dragons
                pass
            info = 'Configuration saved to\n{0}.'.format(configfullname)
            QtGui.QMessageBox.information(
                None, 'Info', info, QtGui.QMessageBox.Ok)

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


def get_config_from_game_id(game_id, db):
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



class SearchGameList(threading.Thread):
    
    gamelist = []
    gamelist_lock = threading.Lock()
    q = queue.Queue()
    
    def __init__(self, db):
        threading.Thread.__init__(self)
        self.db = db
        
    def run(self):
        while True:
            searchstring = SearchGameList.q.get()
            update_ui = True
            gamelist_int = []
            conn = sqlite3.connect(self.db)
            cursor = conn.cursor()
            cursor.execute("SELECT data,id FROM game WHERE data != ''")
            while SearchGameList.q.qsize() == 0:
                fetched = cursor.fetchone()
                if not fetched:
                    break
                data = zlib.decompress(fetched[0])
                game_id = fetched[1]
                doc = json.loads(data.decode())
                gamename = doc.get('game_name', '')
                platform = doc.get('platform', '')
                if searchstring.lower() in gamename.lower() and platform in ('Amiga', 'CD32', 'CDTV'):
                    gamelist_int.append((game_id, gamename, platform))
            
            else:
                update_ui = False
            
            if update_ui:
                SearchGameList.gamelist_lock.acquire()
                SearchGameList.gamelist = gamelist_int
                ui.listWidgetResults.clear()
                for game in gamelist_int:
                    item = QtGui.QListWidgetItem()
                    ui.listWidgetResults.addItem(item)
                    item.setText('{0} [{1}]'.format(game[1], game[2]))
                SearchGameList.gamelist_lock.release()
            
            cursor.close()
            conn.close()
            SearchGameList.q.task_done()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    LauncherAdd = QtGui.QWidget()
    ui = Ui_LauncherAdd()
    ui.setupUi(LauncherAdd)
    LauncherAdd.show()
    sys.exit(app.exec_())

