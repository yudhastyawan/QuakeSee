from PyQt5 import QtWidgets

class About(QtWidgets.QWidget):
    def __init__(self, parent = None):
        QtWidgets.QWidget.__init__(self, parent)
        self.text = QtWidgets.QTextEdit()
        self.text.setReadOnly(True)
        vlayout = QtWidgets.QVBoxLayout()
        vlayout.addWidget(self.text)
        vlayout.setContentsMargins(0,0,0,0)
        self.setLayout(vlayout)

        self.filename = None

    def get_markdown(self):
        if self.filename != None:
            with open(self.filename, 'r', encoding="utf8") as f:
                mdtext = f.read()
            self.text.setMarkdown(mdtext)
