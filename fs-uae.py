#!/usr/bin/env python3

import sys
import subprocess
import fsuae
from PyQt4 import QtGui, QtCore
from time import sleep
from multiprocessing import Pool


class Floppy:

    unit = 0

    def __init__(self, name, menu, eject_menu):
        self.name = name
        self.menu = menu
        self.eject_menu = eject_menu
        self.unit = Floppy.unit
        Floppy.unit += 1
        self.image = FSUAEtray.emu.getFloppyImagePath(self.unit)
        self.insert_action = self.menu.addAction(self.set_menu_text('(empty)', change=False))
        self.insert_action.triggered.connect(lambda: self.insert(self.unit))
        if not self.image == '':
            self.set_menu_text(self.image)
        self.eject_action = self.eject_menu.addAction('eject ' + self.name)
        self.eject_action.triggered.connect(lambda: self.eject(self.unit))

    def insert(self, unit):
        self.image = self.select_image()
        if not self.image:
            return
        FSUAEtray.emu.setFloppyImagePath(unit, self.image)
        self.set_menu_text(self.image)

    def select_image(self):
        image = QtGui.QFileDialog.getOpenFileName(
            parent=None, caption='Select a disk image', filter=(
                'Floppy disk images (*.adf *.dms *.ipf *.adz);;All Files (*)'))
        return image

    def set_menu_text(self, text, change=True):
        entry = '{0}: {1}'.format(self.name, text)
        if change:
            self.insert_action.setText(entry)
        return entry

    def eject(self, unit):
        FSUAEtray.emu.setFloppyImagePath(unit, '')
        self.set_menu_text('(empty)')


class FSUAEtray(QtGui.QDialogButtonBox):

    emu = fsuae.Emu()

    def __init__(self, icon):
        QtGui.QDialogButtonBox.__init__(self)
        self.icon = icon
        self.run_emulator()
        self.systray = QtGui.QSystemTrayIcon(self.icon, parent=self)
        self.connect_emu()
        self.menu = QtGui.QMenu(parent=None)
        self.eject_menu = QtGui.QMenu(parent=None)
        if FSUAEtray.emu.isConnected():
            self.setup_floppies()
            self.menu.addSeparator()
        self.exit_action = self.menu.addAction('Exit')
        self.exit_action.triggered.connect(self.closeEvent)
        self.systray.activated.connect(self.icon_clicked)
        self.systray.show()

    def run_emulator(self):
        self.pool = Pool(1)
        self.ret = self.pool.apply_async(
            run_fsuae,([sys.argv[1:]]), callback=self.callback)

    def icon_clicked(self, reason):
        if reason == QtGui.QSystemTrayIcon.Context:
            self.menu.exec_(QtGui.QCursor.pos())
        else:
            self.eject_menu.exec_(QtGui.QCursor.pos())

    def setup_floppies(self):
        num_drives = FSUAEtray.emu.getNumFloppyDrives()
        if num_drives > 0:
            self.df0 = Floppy('DF0', self.menu, self.eject_menu)
        if num_drives > 1:
            self.df1 = Floppy('DF1', self.menu, self.eject_menu)
        if num_drives > 2:
            self.df1 = Floppy('DF2', self.menu, self.eject_menu)
        if num_drives > 3:
            self.df1 = Floppy('DF3', self.menu, self.eject_menu)

    def closeEvent(self, event):
        print('quit on closeEvent')
        self.disconnect_emu()
        self.pool.terminate()
        #self.pool.close()
        self.pool.join()
        QtCore.QCoreApplication.instance().quit()
        quit()

    def callback(self, ret):
        print('quit on callback')
        print(ret)
        self.closeEvent(None)

    def disconnect_emu(self):
        FSUAEtray.emu.disconnect()
        error = FSUAEtray.emu.getError()
        if error:
            print(error)

    def connect_emu(self):
        num_tries = 0
        while not FSUAEtray.emu.isConnected() and num_tries < 5:
            sleep(1)
            FSUAEtray.emu.connect()
            print(FSUAEtray.emu.getError())
            num_tries += 1
        if not FSUAEtray.emu.isConnected():
            print('Lua Shell connection error')
            print(FSUAEtray.emu.getError())


def run_fsuae(args):
    ret = subprocess.Popen(['fs-uae'] + args)
    return ret


def main():
    app = QtGui.QApplication(sys.argv)
    style = app.style()
    icon = QtGui.QIcon(style.standardPixmap(QtGui.QStyle.SP_DriveFDIcon))
    tray = FSUAEtray(icon)
    tray.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

