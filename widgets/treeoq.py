from PyQt5 import QtCore, QtWidgets, QtGui

class TreeOQ(QtWidgets.QTreeView):
    def __init__(self, parent = None):
        QtWidgets.QTreeView.__init__(self, parent)
        self.tree_model = QtGui.QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(["property", "value"])
        self.setModel(self.tree_model)
        self.header().resizeSection(0, 175)
        self.setAlternatingRowColors(True)
        # self.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        # self.setStyleSheet("QTreeView::item { padding: 2px }")

        self.tree_list = None
        self.print = print

        self.tree_list = None

        if self.tree_list != None:
            self.input_to_tree_model()

    def input_to_tree_model(self):
        font = QtGui.QFont()
        font.setBold(True)

        for cat_i in list(self.tree_list.keys()):
            cat = self.tree_list[cat_i]
            tree_parent = QtGui.QStandardItem(cat_i)
            tree_parent.setEditable(False)
            if cat != None:
                for txt in cat:
                    tree_childs = [QtGui.QStandardItem(txt[0]), QtGui.QStandardItem()]
                    tree_childs[0].setEditable(False)
                    txt[2] = tree_childs[1]
                    if txt[1] == "path":
                        txt[3] = QTextAndButtonDialog(txt[4])
                    elif txt[1] == "savepath":
                        txt[3] = QTextAndButtonSaveDialog(txt[4])
                    elif txt[1] == "bool":
                        txt[3] = QComboBool()
                    elif txt[1] == "option":
                        txt[3] = QComboOption(txt[4])
                    elif txt[1] == "calendar":
                        txt[3] = QtWidgets.QDateTimeEdit(calendarPopup=True)
                        txt[3].setDisplayFormat("dd/MM/yyyy HH:mm:ss")
                        txt[3].setDateTime(QtCore.QDateTime.currentDateTime())
                    elif txt[1] == "number":
                        txt[3] = QtWidgets.QLineEdit()
                    tree_parent.appendRow(tree_childs)
            self.tree_model.appendRow(tree_parent)
            self.tree_model.setData(tree_parent.index(), font, QtCore.Qt.FontRole)
            if cat != None:
                for txt in cat:
                    self.setIndexWidget(txt[2].index(), txt[3])
        self.expandAll()
        return self.tree_list

class QTextAndButton(QtWidgets.QWidget):
    _signal = QtCore.pyqtSignal()

    def __init__(self, parent = None):
        QtWidgets.QWidget.__init__(self, parent)
        vlay = QtWidgets.QVBoxLayout()
        lay = QtWidgets.QHBoxLayout()
        lay.setContentsMargins(0,0,0,0)
        lay.setSpacing(0)
        self.setLayout(lay)

        self.text = QtWidgets.QTextEdit()
        self.text.setMaximumHeight(50)
        self.button = QtWidgets.QPushButton()
        # self.button.setMaximumHeight(20)
        lay.addWidget(self.text)
        vlay.addWidget(self.button)
        vlay.addStretch(1)
        lay.addLayout(vlay)

class QTextAndButtonDialog(QTextAndButton):
    def __init__(self, args, parent = None):
        QTextAndButton.__init__(self, parent)
        self.button.setText("...")
        self.button.clicked.connect(self.on_btn_click)

        self.args = args

    def on_btn_click(self):
        fileNames, _ = QtWidgets.QFileDialog.getOpenFileNames(self, *self.args)
        if fileNames:
            self.text.setPlainText("\n".join(fileNames))
            self._signal.emit()

class QTextAndButtonSaveDialog(QTextAndButton):
    def __init__(self, args, parent = None):
        QTextAndButton.__init__(self, parent)
        self.button.setText("...")
        self.button.clicked.connect(self.on_btn_click)

        self.args = args

    def on_btn_click(self):
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self, *self.args)
        if fileName:
            self.text.setPlainText(fileName)
            self._signal.emit()

class QComboBool(QtWidgets.QComboBox):
    def __init__(self, parent = None):
        QtWidgets.QComboBox.__init__(self, parent)
        self.addItems(["False", "True"])

class QComboOption(QtWidgets.QComboBox):
    def __init__(self, option, parent = None):
        QtWidgets.QComboBox.__init__(self, parent)
        self.addItems(option)