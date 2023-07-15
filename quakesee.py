from PyQt5 import QtWidgets, uic, QtCore
import sys

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        # Load the UI Page
        uic.loadUi('./ui/main_window.ui', self)

        # modify ui
        self.centralwidget.hide()
        self.tabifyDockWidget(self.dock_editor, self.dock_console)

        # Console
        with open("mdfiles/banner.txt") as f:
            banner = f.read()
        self.py_console.banner = banner
        self.search_by_maps.py_console = self.py_console
        self.search_by_maps.py_editor = self.py_editor
        self.load_data_waveforms.py_console = self.py_console
        self.load_data_waveforms.py_editor = self.py_editor
        self.search_by_maps._push_kernel()
        self.load_data_waveforms._push_kernel()

        # variables
        self.tree_list = {
            "Data" : [
                ["Search By Maps", 0],
                ["Download ISC Catalogue (X)", None],
                ["Load Waveform Data", 4],
                ["Load Station Data (X)", None],
                ["Continuous Data (X)", None]
            ],
            "Utilities": [
                ["Picking Phases (X)", None],
                ["HVSR (X)", None],
                ["Create OQ Inputs (X)", None],
                ["Raspberry Shake (X)", None],
            ],
            "About": [
                ["References", 1],
                ["How To Contribute", 2],
                ["This Program", 3]
            ]
        }

        self.stacked_main.setCurrentIndex(0)

        self.tree_options.tree_list = self.tree_list
        self.tree_options.print = lambda x: self.search_by_maps.py_console._append_plain_text(x, True)
        self.tree_options.setStackedIndex = self.stacked_main.setCurrentIndex
        self.tree_options.input_to_tree_model()

        self.about_references.filename = "./mdfiles/references.md"
        self.about_references.get_markdown()

        self.about_howtocontribute.filename = "./mdfiles/howtocontribute.md"
        self.about_howtocontribute.get_markdown()

        self.about_thisprogram.filename = "./mdfiles/thisprogram.md"
        self.about_thisprogram.get_markdown()

    def run_kernel(self):
        self.py_console.run_kernel(self.py_editor.toPlainText())
        self.dock_console.raise_()


def main():
    app = QtWidgets.QApplication(sys.argv)
    main = MainWindow()
    main.showMaximized()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()