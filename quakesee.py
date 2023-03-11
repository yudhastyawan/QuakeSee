from PyQt5 import QtWidgets, uic, QtCore
import sys

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        #Load the UI Page
        uic.loadUi('./ui/main_window.ui', self)

        # variables
        self.tree_list = {
            "Data" : [
                ["Search By Maps", 0],
                ["Download ISC Catalogue (X)", None],
                ["Load Data Waveforms", 4],
                ["Load Data Stations (X)", None],
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


def main():
    app = QtWidgets.QApplication(sys.argv)
    main = MainWindow()
    main.showMaximized()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()