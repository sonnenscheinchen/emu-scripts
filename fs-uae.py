#!/usr/bin/env python3

import sys
import subprocess
import fsuae
from PyQt4 import QtGui, QtCore
from time import sleep
from multiprocessing import Pool


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
            self.actions[n].triggered.connect(self.hide)
            
    def hide_menu(self):
        self.hide()

    def mouseReleaseEvent(self, event):
        action = self.activeAction()
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
            parent=None, caption='Select a disk image', filter=(
                'Floppy disk images (*.adf *.dms *.ipf *.adz);;All Files (*)'))
        return image


class Eject(QtGui.QMenu):
    
    def __init__(self, num_drives, emu):
        QtGui.QMenu.__init__(self, parent=None)
        self.emu = emu
        self.actions = [ None ] * num_drives
        #self.actions = []
        for n in range(num_drives):
            if self.emu.getFloppyImagePath(n):
                self.actions[n] = self.addAction('Eject DF{0}'.format(n))
                self.actions[n].setData(n)
                self.actions[n].triggered.connect(self.hide)

    def mouseReleaseEvent(self, event):
        action = self.activeAction()
        if action is None:
            return
        drive_no = action.data()
        self.eject(drive_no)   
    
    def eject(self, drive_no):
        self.emu.setFloppyImagePath(drive_no, '')
    
    def __bool__(self):
        for action in self.actions:
            if action is not None:
                return True
        return False
        


class FSUAEtray(QtGui.QDialogButtonBox):

    def __init__(self, icon, emu):
        QtGui.QDialogButtonBox.__init__(self)
        self.icon = icon
        self.emu = emu
        self.run_emulator()
        self.num_drives = self.connect_emu()
        self.systray = QtGui.QSystemTrayIcon(self.icon, parent=self)
        self.systray.activated.connect(self.icon_clicked)
        self.systray.show()

    def run_emulator(self):
        self.pool = Pool(1)
        self.ret = self.pool.apply_async(
            run_fsuae,([sys.argv[1:]]), callback=self.callback)

    def icon_clicked(self, reason):
        if reason == QtGui.QSystemTrayIcon.Context:
            self.floppy_menu = Floppy(self.num_drives, self.emu)
            self.floppy_menu.exec_(QtGui.QCursor.pos())
        else:
            self.eject_menu = Eject(self.num_drives, self.emu)
            if self.eject_menu:
                self.eject_menu.exec_(QtGui.QCursor.pos())

    def closeEvent(self, event):
        print('quit on closeEvent')
        self.disconnect_emu()
        self.pool.terminate()
        QtCore.QCoreApplication.instance().quit()

    def callback(self, ret):
        print('quit on callback')
        self.closeEvent(None)

    def disconnect_emu(self):
        self.emu.disconnect()
        error = self.emu.getError()
        if error:
            print(error)

    def connect_emu(self):
        num_tries = 0
        while not self.emu.isConnected() and num_tries < 5:
            sleep(2)
            self.emu.connect()
            print(self.emu.getError())
            num_tries += 1
        if not self.emu.isConnected():
            print('Lua Shell connection error')
            print(self.emu.getError())
            return 0
        else:
            return self.emu.getNumFloppyDrives()

def run_fsuae(args):
    ret = subprocess.call(['fs-uae'] + args)
    return ret


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

