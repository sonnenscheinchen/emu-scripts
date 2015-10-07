#!/usr/bin/env python3
import subprocess
import os
import sys
import fsuae
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QProcess, QTimer

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


def get_floppylist():
    floppylist = []
    basedir = get_basedir()
    if basedir is None:
        return floppylist
    uaelog = os.path.join(basedir, 'Cache', 'Logs', 'debug.uae')
    if not os.path.isfile(uaelog):
        return floppylist
    with open(uaelog, 'rt') as f:
        for line in f:
            if line.startswith('diskimage'):
                image = line.split('=')[1].strip()
                if os.path.isfile(image):
                    floppylist.append(os.path.realpath(image))
    return floppylist


class Floppy(QtWidgets.QMenu):

    def __init__(self, num_drives, shell, floppylist):
        QtWidgets.QMenu.__init__(self, parent=None)
        self.shell = shell
        self.num_drives = num_drives
        for n in range(self.num_drives):
            floppy = self.shell.getFloppyImagePath(n)
            if not floppy:
                floppy = '(empty)'
            action = self.addAction('DF{0}: {1}'.format(n, floppy))
            action.setData((n, None))
        self.triggered.connect(self.menuitem_clicked)
        if len(floppylist) > 0:
            self.add_floppylist_menu(floppylist)

    def menuitem_clicked(self, action):
        drive_no, image = action.data()
        self.insert(drive_no, image)

    def insert(self, drive_no, image):
        if image is None:
            image = self.select_image()
        if image is '':
            return
        self.shell.setFloppyImagePath(drive_no, image)

    def select_image(self):
        image, filter = QtWidgets.QFileDialog.getOpenFileName(
            parent=self, caption='Select a disk image', filter=(
                'Floppy disk images (*.adf *.dms *.ipf *.adz);;All Files (*)'))
        return image

    def add_floppylist_menu(self, floppylist):
            self.addSeparator()
            submenu = self.addMenu('Floppy List')
            for floppy in floppylist:
                subsubmenu = submenu.addMenu(floppy)
                for n in range(self.num_drives):
                    action = subsubmenu.addAction('Into DF{0}:'.format(n))
                    action.setData((n, floppy))
            subsubmenu.triggered.connect(self.menuitem_clicked)


class Eject(QtWidgets.QMenu):

    def __init__(self, num_drives, shell):
        QtWidgets.QMenu.__init__(self, parent=None)
        self.shell = shell
        for n in range(num_drives):
            if self.shell.getFloppyImagePath(n):
                action = self.addAction('Eject DF{0}'.format(n))
                action.setData(n)
        self.triggered.connect(self.menuitem_clicked)

    def menuitem_clicked(self, action):
        drive_no = action.data()
        self.eject(drive_no)

    def eject(self, drive_no):
        self.shell.setFloppyImagePath(drive_no, '')


class FSUAEtray(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.style = QtWidgets.QApplication.style()
        self.icon = QtGui.QIcon(self.style.standardIcon(
            QtWidgets.QStyle.SP_DriveFDIcon))
        self.systray = QtWidgets.QSystemTrayIcon(self.icon, parent=self)
        self.systray.show()
        self.shell = fsuae.Emu()
        self.num_tries = 0
        self.timer = QTimer()
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.connect_shell)
        self.run_emulator()
        self.systray.activated.connect(self.on_icon_clicked)

    def run_emulator(self):
        self.proc = QProcess(self)
        self.proc.started.connect(self.timer.start)
        self.proc.finished.connect(self.exit_app)
        self.proc.error.connect(self.on_error)
        self.proc.setProcessChannelMode(QProcess.ForwardedChannels)
        self.proc.start('fs-uae', ['--lua_shell=1'] + sys.argv[1:])

    def on_icon_clicked(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.Context:
            self.menu = Floppy(self.num_drives, self.shell, self.floppylist)
        else:
            self.menu = Eject(self.num_drives, self.shell)
        if not self.menu.isEmpty():
            self.menu.exec_(QtGui.QCursor.pos())

    def on_error(self, error):
        if error == QProcess.FailedToStart:
            QtWidgets.QMessageBox.critical(
                None, 'Error', 'Failed to start FS-UAE',
                QtWidgets.QMessageBox.Ok)
        self.exit_app(127)

    def exit_app(self, returncode, status=None):
        QtWidgets.QApplication.instance().exit(returncode)

    def connect_shell(self):
        if self.shell.isConnected():
            print('connection established.')
            self.timer.stop()
            self.num_drives = self.shell.getNumFloppyDrives()
            self.floppylist = get_floppylist()
        elif self.num_tries > 4:
            print('lua shell connection error')
            self.timer.stop()
            error = self.shell.getError()
            sys.stderr.write('{0}\n'.format(error))
            self.systray.showMessage('Lua Shell connection error', error)
            self.num_drives = 0
            self.floppylist = []
        else:
            print('connecting...')
            self.shell.connect()
            self.num_tries += 1


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    tray = FSUAEtray()
    sys.exit(app.exec_())
