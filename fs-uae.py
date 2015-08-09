#!/usr/bin/env python3

import subprocess
import os
import sys
import fsuae
from PyQt5 import QtWidgets, QtGui, QtCore
from time import sleep

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

    def __init__(self, num_drives, emu, floppylist):
        QtWidgets.QMenu.__init__(self, parent=None)
        self.emu = emu
        self.num_drives = num_drives
        for n in range(self.num_drives):
            floppy = self.emu.getFloppyImagePath(n)
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
        self.emu.setFloppyImagePath(drive_no, image)

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

    def __init__(self, num_drives, emu):
        QtWidgets.QMenu.__init__(self, parent=None)
        self.emu = emu
        for n in range(num_drives):
            if self.emu.getFloppyImagePath(n):
                action = self.addAction('Eject DF{0}'.format(n))
                action.setData(n)
        self.triggered.connect(self.menuitem_clicked)

    def menuitem_clicked(self, action):
        drive_no = action.data()
        self.eject(drive_no)

    def eject(self, drive_no):
        self.emu.setFloppyImagePath(drive_no, '')


class FSUAEtray(QtWidgets.QSystemTrayIcon):

    def __init__(self, icon, emu, parent=None):
        QtWidgets.QSystemTrayIcon.__init__(self, icon, parent=parent)
        self.emu = emu
        self.run_emulator()
        connection_error = self.connect_emu()
        if connection_error:
            QtWidgets.QMessageBox.warning(None, 'Lua Shell connection error',
                                          connection_error,
                                          QtWidgets.QMessageBox.Ok)
            self.num_drives = 0
            self.floppylist = []
        else:
            self.num_drives = self.emu.getNumFloppyDrives()
            self.floppylist = get_floppylist()
        self.activated.connect(self.icon_clicked)
        self.show()

    def run_emulator(self):
        self.proc = QtCore.QProcess(self)
        self.proc.finished.connect(self.exit_app)
        self.proc.error.connect(self.exit_app)
        self.proc.setProcessChannelMode(QtCore.QProcess.ForwardedChannels)
        self.proc.start('fs-uae', sys.argv[1:])

    def icon_clicked(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.Context:
            self.menu = Floppy(self.num_drives, self.emu, self.floppylist)
        else:
            self.menu = Eject(self.num_drives, self.emu)
        if not self.menu.isEmpty():
            self.menu.exec_(QtGui.QCursor.pos())

    def exit_app(self, returncode):
        self.deleteLater()
        sys.exit(returncode)

    def connect_emu(self):
        num_tries = 0
        while not self.emu.isConnected() and num_tries < 5:
            sleep(2)
            self.emu.connect()
            num_tries += 1
        if not self.emu.isConnected():
            error = self.emu.getError()
            sys.stderr.write(error + '\n')
            return error
        else:
            return None


def main():
    emu = fsuae.Emu()
    app = QtWidgets.QApplication(sys.argv)
    style = app.style()
    icon = QtGui.QIcon(style.standardIcon(QtWidgets.QStyle.SP_DriveFDIcon))
    tray = FSUAEtray(icon, emu)
    tray.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

