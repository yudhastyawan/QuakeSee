from PyQt5 import QtCore

class Communicate(QtCore.QObject):
    sig = QtCore.pyqtSignal(int)
    sigStr = QtCore.pyqtSignal(str)
    sigEmpty = QtCore.pyqtSignal()