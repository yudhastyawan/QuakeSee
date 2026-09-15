from PyQt5 import QtCore

class Communicate(QtCore.QObject):
    sig = QtCore.pyqtSignal(int)
    sigStr = QtCore.pyqtSignal(str)
    sigEmpty = QtCore.pyqtSignal()

class TableModel(QtCore.QAbstractTableModel):
    """
    source: https://www.pythonguis.com/tutorials/pyqt6-qtableview-modelviews-numpy-pandas/
    """
    def __init__(self, data):
        super(TableModel, self).__init__()
        self._data = data

    def data(self, index, role):
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            value = self._data.iloc[index.row(), index.column()]
            return str(value)

    def rowCount(self, index):
        return self._data.shape[0]

    def columnCount(self, index):
        return self._data.shape[1]

    def headerData(self, section, orientation, role):
        # section is the index of the column/row.
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if orientation == QtCore.Qt.Orientation.Horizontal:
                return str(self._data.columns[section])

            if orientation == QtCore.Qt.Orientation.Vertical:
                return str(self._data.index[section])