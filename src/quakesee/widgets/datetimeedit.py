from PyQt5 import QtCore, QtWidgets

class DateTimeEdit(QtWidgets.QDateTimeEdit):
    def __init__(self, parent = None):
        QtWidgets.QDateTimeEdit.__init__(self, parent)

        self.dateTimeChanged.connect(lambda: self.dt_method())
  
    # method called by the datetime
    def dt_method(self):
        # getting current datetime
        self.value = self.dateTime()