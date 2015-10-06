#!/usr/bin/env python3
from PyQt5 import QtCore, QtGui, QtWidgets
import sys
import os
import json
import sqlite3
from binascii import unhexlify
import zlib
import subprocess
import queue


class SearchGameList(QtCore.QThread):
    
    sig = QtCore.pyqtSignal(list)
    
    def __init__(self, db, q):
        super().__init__()
        self.db = db
        self.q = q
        
    def run(self):
        while True:
            searchstring = self.q.get()
            if searchstring is None:
                break
            update_ui = True
            gamelist_int = []
            conn = sqlite3.connect(self.db)
            cursor = conn.cursor()
            cursor.execute("SELECT data,id FROM game WHERE data != ''")
            while self.q.qsize() == 0:
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
                self.sig.emit(gamelist_int)
            self.q.task_done()
            cursor.close()
            conn.close()


class FSUtil:
    
    @staticmethod
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
    
    @staticmethod
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


class LauncherAdd(QtWidgets.QWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.worker = None
        self.setupUi()
        self.basedir = FSUtil.get_basedir()
        if not self.basedir:
            self.exit_critical('Could not find fs-uae base dir.')
            return
        self.db = os.path.join(self.basedir, 'Cache', 'oagd.net.sqlite')
        if not os.path.isfile(self.db):
            self.exit_critical('Could not find local game database.')
            return
        self.q = queue.LifoQueue()
        self.worker = SearchGameList(self.db, self.q)
        self.worker.sig.connect(self.handle_gamelist)
        self.worker.start()

    def setupUi(self):
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.resize(400, 300)
        self.setWindowTitle("Launcher Add Game")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self)
        self.frame = QtWidgets.QFrame(self)
        self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.gridLayout = QtWidgets.QGridLayout(self.frame)
        self.lineEditSearchFor = QtWidgets.QLineEdit(self.frame)
        self.gridLayout.addWidget(self.lineEditSearchFor, 0, 1, 1, 2)
        self.labelSearchFor = QtWidgets.QLabel('Search for:', self.frame)
        self.gridLayout.addWidget(self.labelSearchFor, 0, 0, 1, 1)
        self.pushButtonWriteConfig = QtWidgets.QPushButton('Write Config', self.frame)
        self.pushButtonWriteConfig.setDisabled(True)
        self.gridLayout.addWidget(self.pushButtonWriteConfig, 2, 2, 1, 1)
        self.listWidgetResults = QtWidgets.QListWidget(self.frame)
        self.gridLayout.addWidget(self.listWidgetResults, 1, 0, 1, 3)
        self.horizontalLayout.addWidget(self.frame)
        self.pushButtonWriteConfig.clicked.connect(self.writeconfig)
        self.lineEditSearchFor.textChanged.connect(self.searchdb)
        self.listWidgetResults.itemClicked.connect(self.writeconfig_enable)
        
        
    def searchdb(self):
        self.pushButtonWriteConfig.setDisabled(True)
        searchfor = self.lineEditSearchFor.text()
        if len(searchfor) < 4:
            self.listWidgetResults.clear()
            return
        self.q.put(searchfor)
        
    def writeconfig_enable(self):
        self.pushButtonWriteConfig.setDisabled(False)

    def writeconfig(self):
        self.pushButtonWriteConfig.setDisabled(True)
        self.q.join()
        entry = self.listWidgetResults.currentRow()
        game_id = self.gamelist[entry][0]
        gameconfig = FSUtil.get_config_from_game_id(game_id, self.db)
        configname = '{0} [custom].fs-uae'.format(gameconfig.get('game_name'))
        configfullname = os.path.join(self.basedir, 'Configurations', configname)
        with open(configfullname, 'wt') as f:
            f.write('[fs-uae]\n')
            for option in gameconfig:
                if not option.startswith('__') and not option == 'platform':
                    f.write('{0} = {1}\n'.format(option, gameconfig[option]))
            if gameconfig.get('platform') == 'Amiga':
                if '[AGA]' in gameconfig.get('game_name'):
                    fsuaeconf.write('amiga_model = A1200\n')
            elif gameconfig.get('platform') == 'CD32':
                f.write('amiga_model = CD32\n')
            elif gameconfig.get('platform') == 'CDTV':
                f.write('amiga_model = CDTV\n')
            self.show_info('Configuration saved to\n{0}.'.format(configfullname))
    
    def handle_gamelist(self, gamelist):
        self.gamelist = gamelist
        self.listWidgetResults.clear()
        for game in gamelist:
            item = QtWidgets.QListWidgetItem('{0} [{1}]'.format(game[1], game[2]))
            self.listWidgetResults.addItem(item)

    def exit_critical(self, msg):
        msg = QtWidgets.QMessageBox.critical(
                None, 'Error', msg, QtWidgets.QMessageBox.Ok)
        self.close()
    
    def show_info(self, info):
        msg = QtWidgets.QMessageBox.information(
                None, 'Info', info, QtWidgets.QMessageBox.Ok)
    
    def closeEvent(self, event):
        if self.worker is not None:
            self.q.put(None)
            self.worker.wait()
        event.accept()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    ui = LauncherAdd()
    ui.show()
    sys.exit(app.exec_())
