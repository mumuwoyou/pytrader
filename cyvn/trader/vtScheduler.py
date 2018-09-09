# -*- coding: utf-8 -*-

import sys, os, signal
from qtpy.QtWidgets import QApplication
from cyvn.trader.mainDialog import Ui_Dialog
from qtpy import QtWidgets, QtGui, QtCore

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
class PragramLoader(QtWidgets.QMainWindow):
    pId = None
    scheduler = None
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        self.ui = Ui_Dialog()
        self.cw = QtWidgets.QWidget()
        self.setCentralWidget(self.cw)
        self.ui.setupUi(self.cw)
        self.setWindowTitle(u'定时器')
        self.resize(320, 100)
        self.center()
        self.show()
        self.ui.loadButton.clicked.connect(self.loadFile)
        self.ui.closeButton.clicked.connect(self.closeFile)
        self.ui.startButton.clicked.connect(self.startjob)
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(self.loadFile, 'cron', minute='45', hour='8,20', day_of_week='0-4')
        self.scheduler.add_job(self.closeFile, 'cron', minute='30', hour='15', day_of_week='0-4')
        self.scheduler.add_job(self.closeFile, 'cron', minute='50', hour='2', day_of_week='1-5')

    def center(self):
        qr = self.frameGeometry()
        cp = QtWidgets.QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def getFilename(self):
        filename = 'run_simple.py'
        path = os.path.abspath(os.path.dirname(__file__))
        return os.path.join(path, filename)

    def loadFile(self):
        extra = ['default']
        fn = self.getFilename()
        if fn is None:
            return
        if sys.platform.startswith('win'):
            self.pId = os.spawnl(os.P_NOWAIT, sys.executable, '"' + sys.executable + '"', '"' + fn + '"', *extra)
        else:
            self.pId = os.spawnl(os.P_NOWAIT, sys.executable, sys.executable, fn, *extra)

    def closeFile(self):
        if self.pId != None:
            os.kill(self.pId, signal.SIGKILL)

    def startjob(self):
        if self.ui.startButton.text() == u'开始':
            try:
                self.scheduler.start()
                self.ui.startButton.setText(u'停止')
            except(KeyboardInterrupt, SystemExit):
                self.scheduler.shutdown()
                self.ui.startButton.setText(u'开始')
        else:
            self.scheduler.shutdown()
            self.ui.startButton.setText(u'开始')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    loader = PragramLoader()
    sys.exit(app.exec_())
