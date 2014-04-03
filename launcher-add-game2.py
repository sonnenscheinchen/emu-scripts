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


try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_LauncherAdd(object):
    def setupUi(self, LauncherAdd):
        LauncherAdd.setObjectName(_fromUtf8("LauncherAdd"))
        LauncherAdd.resize(372, 243)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(LauncherAdd.sizePolicy().hasHeightForWidth())
        LauncherAdd.setSizePolicy(sizePolicy)
        self.horizontalLayout = QtGui.QHBoxLayout(LauncherAdd)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.frame = QtGui.QFrame(LauncherAdd)
        self.frame.setFrameShape(QtGui.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtGui.QFrame.Raised)
        self.frame.setObjectName(_fromUtf8("frame"))
        self.gridLayout = QtGui.QGridLayout(self.frame)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.lineEditSearchFor = QtGui.QLineEdit(self.frame)
        self.lineEditSearchFor.setObjectName(_fromUtf8("lineEditSearchFor"))
        self.gridLayout.addWidget(self.lineEditSearchFor, 0, 1, 1, 1)
        self.labelSearchFor = QtGui.QLabel(self.frame)
        self.labelSearchFor.setObjectName(_fromUtf8("labelSearchFor"))
        self.gridLayout.addWidget(self.labelSearchFor, 0, 0, 1, 1)
        self.pushButtonSearch = QtGui.QPushButton(self.frame)
        self.pushButtonSearch.setObjectName(_fromUtf8("pushButtonSearch"))
        self.gridLayout.addWidget(self.pushButtonSearch, 0, 2, 1, 1)
        self.pushButtonWriteConfig = QtGui.QPushButton(self.frame)
        self.pushButtonWriteConfig.setObjectName(_fromUtf8("pushButtonWriteConfig"))
        self.gridLayout.addWidget(self.pushButtonWriteConfig, 2, 2, 1, 1)
        self.listWidgetResults = QtGui.QListWidget(self.frame)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.listWidgetResults.sizePolicy().hasHeightForWidth())
        self.listWidgetResults.setSizePolicy(sizePolicy)
        self.listWidgetResults.setObjectName(_fromUtf8("listWidgetResults"))
        self.gridLayout.addWidget(self.listWidgetResults, 1, 0, 1, 3)
        self.horizontalLayout.addWidget(self.frame)

        self.retranslateUi(LauncherAdd)
        QtCore.QMetaObject.connectSlotsByName(LauncherAdd)

        ##!!!##
        self.pushButtonSearch.clicked.connect(self.searchdb)
        self.pushButtonWriteConfig.clicked.connect(self.writeconfig)
        self.lineEditSearchFor.returnPressed.connect(self.searchdb)

    def retranslateUi(self, LauncherAdd):
        LauncherAdd.setWindowTitle(_translate("LauncherAdd", "Launcher Add", None))
        self.labelSearchFor.setText(_translate("LauncherAdd", "Search for:", None))
        self.pushButtonSearch.setText(_translate("LauncherAdd", "Search", None))
        self.pushButtonWriteConfig.setText(_translate("LauncherAdd", "Write Config", None))

    def searchdb(self):
        self.searchfor = self.lineEditSearchFor.text()
        if len(self.searchfor) < 4:
            self.lineEditSearchFor.setText('')
            ## FIXME: warn user ##
            return
        self.gamelist = get_gamelist_from_searchstring(self.searchfor)
        #print(self.gamelist)
        self.listWidgetResults.clear()
        for self.game in self.gamelist:
            item = QtGui.QListWidgetItem()
            self.listWidgetResults.addItem(item)
            item.setText('{0} [{1}]'.format(self.game[1], self.game[2]))

    def writeconfig(self):
        #self.entry = self.listWidgetResults.currentItem()
        self.entry = self.listWidgetResults.currentRow()
        print(self.entry)
        if not self.entry > -1:
            ## FIXME: warn user ##
            return
        gameconfig = get_config_from_game_id(self.gamelist[self.entry][0])
        #print(gameconfig)
        configname = '{0} [custom].fs-uae'.format(gameconfig.get('game_name'))
        configfullname = os.path.join(basedir, 'Configurations', configname)
        with open(configfullname, 'wt') as fsuaeconf:
            fsuaeconf.write('[fs-uae]\n')
            for option in gameconfig:
                print(option)
                if not option.startswith('__') and not option == 'platform':
                    print('wrote ' + option)
                    fsuaeconf.write('{0} = {1}\n'.format(
                        option, gameconfig[option]))
            if gameconfig.get('platform') == 'Amiga':
                #[fsuaeconf.write('floppy_drive_{0} = {1}\n'.format(
                #    floppyno, floppy)) for floppyno, floppy in zip(range(4), floppylist)]
                #[fsuaeconf.write('floppy_image_{0} = {1}\n'.format(
                #    floppyimageno, floppyimagefile)) for floppyimageno, floppyimagefile in zip(
                #        range(20), floppylist)]
                if '[AGA]' in gameconfig.get('game_name'):
                    fsuaeconf.write('amiga_model = A1200\n')
            elif gameconfig.get('platform') == 'CD32':
                #fsuaeconf.write('cdrom_drive_0 = {0}\n'.format(floppylist[0]))
                fsuaeconf.write('amiga_model = CD32\n')
            elif gameconfig.get('platform') == 'CDTV':
                #fsuaeconf.write('cdrom_drive_0 = {0}\n'.format(floppylist[0]))
                fsuaeconf.write('amiga_model = CDTV\n')
            else:
                #here be dragons
                pass


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


def get_gamelist_from_searchstring(searchstring, fileplatform='Amiga, CD32, CDTV'):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute("SELECT data,id FROM game")
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
        if searchstring.lower() in gamename.lower() and platform in fileplatform:
            gamelist.append((game_id, gamename, platform))
    cursor.close()
    conn.close()
    return gamelist



if __name__ == "__main__":
    global basedir
    basedir = get_basedir()
    if not basedir:
        sys.stderr.write('Could not find fs-uae base dir.\n')
        quit(1)

    global db
    db = os.path.join(basedir, 'Data', 'Game Database.sqlite')
    if not os.path.isfile(db):
        sys.stderr.write('Could not find local game database.\n')
        quit(1)

    app = QtGui.QApplication(sys.argv)
    LauncherAdd = QtGui.QWidget()
    ui = Ui_LauncherAdd()
    ui.setupUi(LauncherAdd)
    LauncherAdd.show()
    sys.exit(app.exec_())

