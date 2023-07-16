"""
Author: Yudha Styawan

Feel free to use this program, thank you!
"""

from PyQt5 import QtWidgets, uic, QtCore
import sys

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        # Load the UI Page
        uic.loadUi('./ui/main_window.ui', self)

        # Modify ui
        # - we do not use central widget
        self.centralwidget.hide()
        # - editor and console should be grouped into a tab
        self.tabifyDockWidget(self.dock_editor, self.dock_console)

        # Console
        # - read text banner that would be shown in the python console
        with open("mdfiles/banner.txt") as f:
            banner = f.read()
        self.py_console.banner = banner
        # - each window console need to be connected to the main console -> push kernel
        self.search_by_maps.py_console = self.py_console
        self.search_by_maps.py_editor = self.py_editor
        self.load_data_waveforms.py_console = self.py_console
        self.load_data_waveforms.py_editor = self.py_editor
        self.search_by_maps._push_kernel()
        self.load_data_waveforms._push_kernel()

        # Generate the main tree list
        # - (X) denotes the unimplemented features
        # - the second element of each list represents the location within the main stack widget
        self.tree_list = {
            "Data" : [
                ["Search By Maps", 0],
                ["Download ISC Catalogue (X)", None],
                ["Load Waveform Data", 4],
                ["Load Station Data (X)", None],
                ["Continuous Data (X)", None]
            ],
            "Utilities": [
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

        # Set the current location of the main stack widget
        self.stacked_main.setCurrentIndex(0)

        # Settings of the tree options (treeoptions.py)
        self.tree_options.tree_list = self.tree_list
        self.tree_options.print = lambda x: self.search_by_maps.py_console._append_plain_text(x, True)
        self.tree_options.setStackedIndex = self.stacked_main.setCurrentIndex
        self.tree_options.input_to_tree_model()

        # References
        self.about_references.filename = "./mdfiles/references.md"
        self.about_references.get_markdown()

        # How to Contribute
        self.about_howtocontribute.filename = "./mdfiles/howtocontribute.md"
        self.about_howtocontribute.get_markdown()

        # About This Program
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