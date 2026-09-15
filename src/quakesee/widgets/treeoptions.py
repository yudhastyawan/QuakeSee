from PyQt5 import QtCore, QtWidgets, QtGui

class TreeOptions(QtWidgets.QTreeView):
    def __init__(self, parent = None):
        QtWidgets.QTreeView.__init__(self, parent)
        self.tree_model = QtGui.QStandardItemModel()
        self.setModel(self.tree_model)

        self.tree_list = None
        self.print = print
        self.setStackedIndex = lambda x: self.print(f"{x}")

        if self.tree_list != None:
            self.input_to_tree_model()

        self.clicked.connect(self.on_click)

    def input_to_tree_model(self):
        for cat_i in list(self.tree_list.keys()):
            cat = self.tree_list[cat_i]
            tree_parent = QtGui.QStandardItem(cat_i)
            tree_parent.setEditable(False)
            if cat != None:
                for txt in cat:
                    tree_child = QtGui.QStandardItem(txt[0])
                    tree_child.setEditable(False)
                    tree_parent.appendRow(tree_child)
            self.tree_model.appendRow(tree_parent)
        self.expandAll()

    def on_click(self, sel:QtCore.QModelIndex):
        if sel.parent().row() != -1:
            key = list(self.tree_list.keys())[sel.parent().row()]
            if self.tree_list[key][sel.row()][1] != None:
                self.setStackedIndex(self.tree_list[key][sel.row()][1])