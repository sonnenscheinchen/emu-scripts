#!/usr/bin/env python3

import sys
import fsuae
from PyQt4 import QtGui, QtCore
from time import sleep


class Floppy(QtGui.QMenu):
    
    def __init__(self, num_drives, emu):
        QtGui.QMenu.__init__(self, parent=None)
        self.emu = emu
        self.actions = [ None ] * num_drives
        for n in range(num_drives):
            floppy = self.emu.getFloppyImagePath(n)
            if not floppy:
                floppy = '(empty)'
            self.actions[n] = self.addAction('DF{0}: {1}'.format(n, floppy))
            self.actions[n].setData(n)

    def mouseReleaseEvent(self, event):
        action = self.activeAction()
        event.accept()
        if action is None:
            return
        drive_no = action.data()
        self.insert(drive_no)
    
    def insert(self, drive_no):
        image = self.select_image()
        if not image:
            return
        self.emu.setFloppyImagePath(drive_no, image)

    def select_image(self):
        image = QtGui.QFileDialog.getOpenFileName(
            parent=self, caption='Select a disk image', filter=(
                'Floppy disk images (*.adf *.dms *.ipf *.adz);;All Files (*)'))
        return image


class Eject(QtGui.QMenu):
    
    def __init__(self, num_drives, emu):
        QtGui.QMenu.__init__(self, parent=None)
        self.emu = emu
        self.actions = [ None ] * num_drives
        for n in range(num_drives):
            if self.emu.getFloppyImagePath(n):
                self.actions[n] = self.addAction('Eject DF{0}'.format(n))
                self.actions[n].setData(n)

    def mouseReleaseEvent(self, event):
        action = self.activeAction()
        event.accept()
        if action is None:
            return
        drive_no = action.data()
        self.eject(drive_no)   
    
    def eject(self, drive_no):
        self.emu.setFloppyImagePath(drive_no, '')


class FSUAEtray(QtGui.QDialogButtonBox):

    def __init__(self, icon, emu):
        QtGui.QDialogButtonBox.__init__(self)
        self.icon = icon
        self.emu = emu
        self.run_emulator()
        connection_error = self.connect_emu()
        if connection_error:
            QtGui.QMessageBox.warning(self, 'Lua Shell connection error',
                                      connection_error,
                                      QtGui.QMessageBox.Ok)
            self.num_drives = 0
        else:
            self.num_drives = self.emu.getNumFloppyDrives()
        self.systray = QtGui.QSystemTrayIcon(self.icon, parent=self)
        self.systray.activated.connect(self.icon_clicked)
        self.systray.show()

    def run_emulator(self):
        self.proc = QtCore.QProcess(self)
        self.proc.finished.connect(self.exit_app)
        self.proc.error.connect(self.exit_app)
        self.proc.setProcessChannelMode(QtCore.QProcess.ForwardedChannels)
        self.proc.start('fs-uae', sys.argv[1:])

    def icon_clicked(self, reason):
        if reason == QtGui.QSystemTrayIcon.Context:
            self.menu = Floppy(self.num_drives, self.emu)
        else:
            self.menu = Eject(self.num_drives, self.emu)
        if not self.menu.isEmpty():
            self.menu.exec_(QtGui.QCursor.pos())

    def exit_app(self, returncode):
        self.close()
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
    app = QtGui.QApplication(sys.argv)
    style = app.style()
    icon = QtGui.QIcon(style.standardPixmap(QtGui.QStyle.SP_DriveFDIcon))
    tray = FSUAEtray(icon, emu)
    tray.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

