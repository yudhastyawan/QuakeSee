from PyQt5 import QtCore

class Worker(QtCore.QObject):
    finished = QtCore.pyqtSignal()
    progress = QtCore.pyqtSignal(str)
    progress_int = QtCore.pyqtSignal(int)

    def __init__(self, func, parent = None):
        QtCore.QObject.__init__(self, parent)
        self.func = func
    
    def run(self):
        self.func()
        self.finished.emit()

