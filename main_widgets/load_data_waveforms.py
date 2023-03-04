from PyQt5 import QtWidgets, uic
import obspy as ob

class LoadDataWaveforms(QtWidgets.QWidget):
    def __init__(self, parent = None):
        QtWidgets.QWidget.__init__(self, parent)

        #Load the UI Page
        uic.loadUi('./ui/load_data_waveforms.ui', self)

        self.tree_list = {
            "Waveforms": [
                ["path", "path", None, None],
            ],
            "Event (X)": [
                ["datetime", "calendar", None, None],
                ["longitude", "number", None, None],    
                ["latitude", "number", None, None],
            ],
            "Stations (X)": [
                ["path", "path", None, None],
                ["distance", "bool", None, None],
            ],
            "Selection (X)": [
                ["apply", "bool", None, None],
                ["network", "number", None, None],    
                ["station", "number", None, None],
                ["channel", "number", None, None],
                ["component", "number", None, None],
            ],
            "Precondition (X)": [
                ["remove mean", "bool", None, None],
                ["remove trend", "bool", None, None],
            ],
            "Filter (X)": [
                ["apply", "bool", None, None],
                ["minfreq", "number", None, None],    
                ["maxfreq", "number", None, None],
            ]
        }

        self.data = {
            "waveforms": None,
        }

        kernel_dict = {
            "self":self
        }

        self.py_console.push_kernel(kernel_dict)

        self._print = lambda x: self.py_console._append_plain_text(x, True)
        self._printLn = lambda x: self._print(x + "\n")
        self._printLn2 = lambda x: self._print("\n" + x + "\n")

        self.tree_main.tree_list = self.tree_list
        self.tree_list = self.tree_main.input_to_tree_model()

        self.tab_code.hide()

    def run_kernel(self):
        self.py_console.run_kernel(self.py_editor.toPlainText())
        self.tab_code.setCurrentIndex(0)

    def _on_btn_apply_clicked(self):
        self._modify_waveforms()
        fig = self.tab_waveplots.widgetCanvas.mpl.axes.figure
        fig.clf()
        if self.data["waveforms"] != None:
            len_waveforms = len(self.data["waveforms"])
            self.data["waveforms"].plot(fig=fig)
            self.tab_waveplots.widgetCanvas.setMinimumSize(self.tab_waveplots.widgetCanvas.width(), 100*len_waveforms)

    def _modify_waveforms(self):
        fileNames = self.tree_list['Waveforms'][0][3].text.toPlainText()
        try:
            for i, fn in enumerate(fileNames.split('\n')):
                if i == 0:
                    self.data["waveforms"] = ob.read(fn)
                else:
                    self.data["waveforms"] += ob.read(fn)
        except:
            self._printLn("The data cannot be load.")
            self.data["waveforms"] = None

    def _on_btn_saveas_waveforms_clicked(self):
        self._modify_waveforms()
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Waveforms", "", "MSEED Files (*.mseed)")
        if fileName:
            if self.data["waveforms"] != None:
                self.data["waveforms"].write(fileName, format="MSEED")
                self._printLn2(f"saving waveform data to {fileName}")