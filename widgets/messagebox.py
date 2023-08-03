from PyQt5 import QtWidgets, uic, QtCore

class MBox(QtWidgets.QDialog):
    def __init__(self, txt_lbl, txt_error, parent = None):
        QtWidgets.QWidget.__init__(self, parent, QtCore.Qt.Window | QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowStaysOnTopHint)

        #Load the UI Page
        uic.loadUi('./ui/message_box.ui', self)

        self.setWindowTitle("Message: Error")

        self.lbl_error.setText(txt_lbl)
        self.txt_error.setText(txt_error)

        self.show()

class MBoxLbl(QtWidgets.QDialog):
    def __init__(self, txt_lbl, parent = None):
        QtWidgets.QWidget.__init__(self, parent, QtCore.Qt.Window | QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowStaysOnTopHint)

        #Load the UI Page
        uic.loadUi('./ui/message_box_lbl.ui', self)

        self.setWindowTitle("Message: Error")

        self.lbl_error.setText(txt_lbl)

        self.show()