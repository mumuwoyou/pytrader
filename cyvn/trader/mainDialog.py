# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'mainDialog.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from qtpy import QtWidgets, QtGui, QtCore


try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtWidgets.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtWidgets.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtWidgets.QApplication.translate(context, text, disambig)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName(_fromUtf8("Dialog"))
        Dialog.resize(332, 103)
        self.startButton = QtWidgets.QPushButton(Dialog)
        self.startButton.setGeometry(QtCore.QRect(20, 30, 84, 32))
        self.startButton.setObjectName(_fromUtf8("startButton"))
        self.closeButton = QtWidgets.QPushButton(Dialog)
        self.closeButton.setGeometry(QtCore.QRect(220, 30, 84, 32))
        self.closeButton.setObjectName(_fromUtf8("closeButton"))
        self.loadButton = QtWidgets.QPushButton(Dialog)
        self.loadButton.setGeometry(QtCore.QRect(120, 30, 84, 32))
        self.loadButton.setObjectName(_fromUtf8("loadButton"))

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(_translate("Dialog", "定时器", None))
        self.startButton.setText(_translate("Dialog", "开始", None))
        self.closeButton.setText(_translate("Dialog", "关闭", None))
        self.loadButton.setText(_translate("Dialog", "载入", None))

