"""
Author: Yudha Styawan

Feel free to use this program, thank you!
"""

from PyQt5 import QtWidgets, uic, QtCore
import sys
import matplotlib as mpl

mpl.rcParams['savefig.dpi'] = 300

class MainWindow(QtWidgets.QMainWindow):
    """
    Main window of this program.
    """
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
        
        # load during opening program
        banner += self.create_oq._chk_on_program_load()

        self.py_console.banner = banner
        # - each window console need to be connected to the main console -> push kernel
        self.search_by_maps.py_console = self.py_console
        self.search_by_maps.py_editor = self.py_editor
        self.load_data_waveforms.py_console = self.py_console
        self.load_data_waveforms.py_editor = self.py_editor
        self.load_data_stations.py_console = self.py_console
        self.load_data_stations.py_editor = self.py_editor
        self.raspshake.py_console = self.py_console
        self.raspshake.py_editor = self.py_editor
        self.create_oq.py_console = self.py_console
        self.download_isc.py_console = self.py_console
        
        self.search_by_maps._push_kernel()
        self.load_data_waveforms._push_kernel()
        self.load_data_stations._push_kernel()
        self.raspshake._push_kernel()
        self.create_oq._push_kernel()
        self.download_isc._push_kernel()

        # Generate the main tree list
        # - (X) denotes the unimplemented features
        # - the second element of each list represents the location within the main stack widget
        self.tree_list = {
            "Data" : [
                ["Search By Maps", 0],
                ["Download ISC Catalogue", 10],
                ["Load Waveform Data", 4],
                ["Load Station Data", 5],
                ["Continuous Data (X)", None]
            ],
            "Utilities": [
                ["HVSR", 9],
                ["Create OQ Inputs", 6],
                ["Raspberry Shake", 7],
                ["Real-Time Waveforms", 8]
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

        # Menu bar
        self.actionReset_Map.triggered.connect(self.search_by_maps._on_btn_map_reset)
        self.actionSave_Available_Events_csv.triggered.connect(self.search_by_maps._on_btn_save_events_clicked)
        self.actionSave_Selected_Stations_XML.triggered.connect(self.search_by_maps._save_stations)
        self.actionSave_Waveforms_mseed.triggered.connect(self.search_by_maps._save_waveforms)
        self.actionClear_New_Windows.triggered.connect(self.load_data_waveforms._on_btn_clear_windows_clicked)
        self.actionReverse_Strike_in_Selected_Geometries.triggered.connect(self.create_oq.reverse_strike_in_selected_geometries)
        self.actionLoad_to_Load_Waveform_Data.triggered.connect(self.wave_from_map_to_load_waveform_data)
        self.actionShow_Waveforms_in_New_Window.triggered.connect(self.search_by_maps._show_waveforms_in_new_window)
        self.actionConvert_Lonlat_to_Distance_3D.triggered.connect(lambda: self.create_oq._CreateOQ__view_3D_after_fault_cut(True))
        self.actionPreview_3D_Lon_Lat_degree.triggered.connect(lambda: self.create_oq._CreateOQ__view_3D_after_fault_cut(False))
        self.actionLoad_Events.triggered.connect(self.search_by_maps._on_btn_load_events_clicked)
        self.actionSave_Responses_as_SACPZ_SEISAN_filename.triggered.connect(self.load_data_stations._save_seisan_sacpz)
        self.actionLoad_Stations.triggered.connect(self.search_by_maps._load_station_in_map)

    def run_kernel(self):
        self.py_console.run_kernel(self.py_editor.toPlainText())
        self.dock_console.raise_()

    def _on_btn_load_py_clicked(self):
        """
        """
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Python file", "", "Python File (*.py)")
        if fileName:
            try:
                with open(fileName, 'r') as f:
                    self.py_editor.setPlainText(f.read())
            except:
                pass
    
    def _on_btn_save_py_clicked(self):
        """
        """
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Python file", "", "Python File (*.py)")
        if fileName:
            try:
                with open(fileName, 'w') as f:
                    f.write(self.py_editor.toPlainText())
            except:
                pass

    def wave_from_map_to_load_waveform_data(self):
        if self.search_by_maps.data["waveforms"] is not None:
            self.load_data_waveforms._base_waveforms = self.search_by_maps.data["waveforms"]
            self.load_data_waveforms.tree_list["Waveform Location"][1][3].setCurrentIndex(0)
            self.stacked_main.setCurrentIndex(4)
            self.load_data_waveforms._on_btn_apply_clicked()

def main():
    app = QtWidgets.QApplication(sys.argv)
    main = MainWindow()
    main.showMaximized()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()