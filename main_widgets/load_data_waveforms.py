from PyQt5 import QtWidgets, uic, QtCore
import obspy as ob
import os
from libs.commons import Worker
from libs.utils import TableModel
from widgets.mplcanvas import MplCanvasBaseWithToolbar
from obspy.clients.fdsn.header import URL_MAPPINGS
from obspy.clients.fdsn.client import Client
from pyproj import Geod
from matplotlib.transforms import blended_transform_factory
import pandas as pd
import numpy as np
import matplotlib as mpl

class LoadDataWaveforms(QtWidgets.QWidget):
    def __init__(self, parent = None):
        QtWidgets.QWidget.__init__(self, parent)

        #Load the UI Page
        uic.loadUi('./ui/load_data_waveforms.ui', self)

        # modify UI
        self.wid_options.hide()

        self.tree_list = {
            "Waveform Location": [
                ["path", "path", None, None, ("Open Waveforms", "", "MSEED Files (*.mseed *.sac *.SAC)")],
                ["load", "bool", None, None],
            ],
            "Phase (X)": [
                ["path", "path", None, None, ("Open Phase Data", "", "ASCII Files (*.txt *.dat *.csv)")],
                ["load", "bool", None, None],
            ],
            "Plot Options": [
                ["all waveforms", "bool", None, None],
                ["time vs. offsets", "bool", None, None],
                ["map (X)", "bool", None, None],
            ],
            "Event": [
                ["datetime", "calendar", None, None],
                ["longitude", "number", None, None],    
                ["latitude", "number", None, None],
            ],
            "Stations": [
                ["online search", "bool", None, None],
                ["path", "path", None, None, ("Open Stations", "", "XML Files (*.xml)")],
                ["distance", "bool", None, None],
            ],
            "Selection": [
                ["apply", "bool", None, None],
                ["network", "number", None, None],    
                ["station", "number", None, None],
                ["location", "number", None, None],
                ["channel", "number", None, None],
                ["component", "number", None, None],
            ],
            "Precondition": [
                ["merge", "bool", None, None],
                ["remove mean", "bool", None, None],
                ["remove simple trend", "bool", None, None],
                ["remove linear trend", "bool", None, None],
                ["taper (0.05)", "bool", None, None],
            ],
            "Filter": [
                ["apply", "bool", None, None],
                ["minfreq", "number", None, None],    
                ["maxfreq", "number", None, None],
            ],
            "Time vs. Offsets": [
                ["origin time", "bool", None, None],
                ["velocity", "bool", None, None],
                ["Vp (km/s)", "number", None, None],
                ["Vs (km/s)", "number", None, None],
            ]
        }

        self.configs = {
            "base clients": list(URL_MAPPINGS.keys()),
            "selected clients": list(URL_MAPPINGS.keys()),
            "geod reference": 'WGS84',
            "show waveform component": 'Z',
        }

        # configs base
        self.configs_base = self.configs.copy()

        self.data = {
            "origin time": None,
            "event coordinate": [None, None],
            "waveforms": None,
            "selected waveforms": None,
            "stations": None,
            "minimum starttime": None,
        }

        kernel_dict = {
            "_wave":self,
            "wave_configs":self.configs,
            "wave_data":self.data,
            "wave_configs_reset":self.reset_configs
        }

        self.__new_windows = []
        self.__selected_event = None
        self.__plot_rows = None
        self.__wave_df = None
        self.__phase_df = None

        self.thread = None
        self.worker = None

        self._push_kernel = lambda: self.py_console.push_kernel(kernel_dict)

        self._print = lambda x: self.py_console._append_plain_text(x, True)
        self._printLn = lambda x: self._print(x + "\n")
        self._printLn2 = lambda x: self._print("\n" + x + "\n")

        self.tree_main.tree_list = self.tree_list
        self.tree_list = self.tree_main.input_to_tree_model()

        self.tab_time_offsets.mpl.axes.figure.clf()

        ## set default parameter
        self.tree_list["Time vs. Offsets"][2][3].setText("5.55")
        self.tree_list["Time vs. Offsets"][3][3].setText("3.25")
        self.tree_list["Selection"][1][3].setText("*")
        self.tree_list["Selection"][2][3].setText("*")
        self.tree_list["Selection"][3][3].setText("*")
        self.tree_list["Selection"][4][3].setText("*")
        self.tree_list["Selection"][5][3].setText("*")
        self.tree_list["Waveform Location"][1][3].setCurrentIndex(1)

    def __set_table_waves(self):
        data = {"network":[], "station":[], "location":[], "channel":[], "starttime":[], "endtime":[],
                "sampling_rate":[], "delta":[], "npts":[], "calib":[], "_format":[]}
        for tr in self.data["waveforms"]:
            data = {key: value + [tr.stats.__dict__[key]] for key, value in data.items()}
        self.__wave_df = pd.DataFrame.from_dict(data)
        self.__table_model = TableModel(self.__wave_df)
        self.table_waves.setModel(self.__table_model)
        self.table_waves.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_waves.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)

    def __set_table_phase(self):
        data_phase = {"network":[], "station":[], "location":[]}
        P = []
        S = []
        check = ""
        for tr in self.__base_waveforms:
            if check != "".join([tr.stats.__dict__[key] for key in ["network", "station", "location"]]):
                data_phase = {key: data_phase[key] + [tr.stats.__dict__[key]] for key in ["network", "station", "location"]}
                P.append(np.nan)
                S.append(np.nan)
            check = "".join([tr.stats.__dict__[key] for key in ["network", "station", "location"]])
        data_phase["P"] = P
        data_phase["S"] = S
        self.__phase_df = pd.DataFrame.from_dict(data_phase)
        self.__table_phase_model = TableModel(self.__phase_df)
        self.table_phase.setModel(self.__table_phase_model)
        self.table_phase.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_phase.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)

    def contextMenuEvent(self, event):
        self.menu = QtWidgets.QMenu(self.table_waves)
        self.plot_menu = self.menu.addAction("Plot")
        self.plot_menu.triggered.connect(self.__on_plot_menu_clicked)
        self.plot_new_window_menu = self.menu.addAction("Plot in A New Window")
        self.plot_new_window_menu.triggered.connect(self.__on_plot_menu_new_window_clicked)
        self.menu.exec_(event.globalPos())

    def __on_plot_menu_clicked(self):
        self.__plot_rows = [idx.row() for idx in self.table_waves.selectionModel().selectedRows()]
        self.__st = ob.Stream([self.data["waveforms"].traces[i] for i in self.__plot_rows])
        self.__show_waveplots(self.tab_waveplots.widgetCanvas.mpl, self.__st)
        self.__update_mpl_to_tight(self.tab_waveplots.widgetCanvas.mpl)

    def _on_btn_clear_windows_clicked(self):
        if self.__new_windows != []:
            for w in self.__new_windows: w.close()
        del self.__new_windows
        self.__new_windows = []

    def __on_plot_menu_new_window_clicked(self):
        rows = [idx.row() for idx in self.table_waves.selectionModel().selectedRows()]
        self.__st = ob.Stream([self.data["waveforms"].traces[i] for i in rows])
        self.__plot_widget = MplCanvasBaseWithToolbar()
        self.__show_waveplots(self.__plot_widget.mpl, self.__st)
        self.__update_mpl_to_tight(self.__plot_widget.mpl)
        self.__plot_widget.show()
        self.__new_windows.append(self.__plot_widget)

    def reset_configs(self):
        for key in self.configs.keys():
            self.configs[key] = self.configs_base[key]

    def run_kernel(self):
        self.py_console.run_kernel(self.py_editor.toPlainText())
        self.tab_code.setCurrentIndex(0)

    def _on_btn_apply_clicked(self):
        self.pbar_apply.setValue(0)
        self.btn_apply.setEnabled(False)
        self.tab_time_offsets.mpl.axes.figure.clf()
        self.tab_time_offsets.mpl.draw()

        self.thread = QtCore.QThread()
        self.worker = Worker(self._modify_waveforms)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.progress.connect(self._printLn)
        self.worker.progress_int.connect(self.pbar_apply.setValue)
        # self.thread.setTerminationEnabled(True)
        self.thread.start()

        self.thread.finished.connect(
            lambda: self.btn_apply.setEnabled(True)
        )
        
        # self.worker.finished.connect(lambda: self.__show_waveplots())
        self.worker.finished.connect(lambda: self._printLn("finished!"))
        self.worker.finished.connect(lambda: self.__update_mpl_to_tight(self.tab_waveplots.widgetCanvas.mpl))
        self.worker.finished.connect(lambda: self.__set_table_phase())
        self.worker.finished.connect(lambda: self.pbar_apply.setValue(100))
    
    # def terminate_thread(self):
    #     if self.thread != None:
    #         self.thread.terminate()
    #         self._printLn2("process is terminated.")

    def __update_mpl_to_tight(self, mpl):
        if self.data["waveforms"] != None:
            fig = mpl.axes.figure
            fig.tight_layout(pad=0,w_pad=0)
            fig.subplots_adjust(wspace=0, hspace=0)
            mpl.draw()

    def _on_btn_resize_clicked(self):
        if self.data["waveforms"] != None:
            len_waveforms = len(self.data["waveforms"])
            mult = int(self.text_resize.text())
            self.tab_waveplots.widgetCanvas.setMinimumSize(self.tab_waveplots.widgetCanvas.width(), mult*len_waveforms)
    
    def __show_waveplots(self, mpl, st):
        fig = mpl.axes.figure
        fig.clf()
        if st != None:
            len_waveforms = len(st)
            st.plot(fig=fig, equal_scale=False)
            self.tab_waveplots.widgetCanvas.setMinimumSize(self.tab_waveplots.widgetCanvas.width(), 100*len_waveforms)
            # for ax in fig.axes: ax.tick_params(axis="y",direction="in", pad=-22)
            for ax in fig.axes: ax.ticklabel_format(axis='y',style='sci', scilimits=(0,0))
            for ax in fig.axes: ax.margins(0)
            mpl.draw()

        def on_key(event):
            ax = event.inaxes
            if event.key in ['p', 'P']:        
                axs = self.__select_axes(ax, "P", event.xdata)        
                for axi in axs: axi.axvline(event.xdata, picker=5)
                mpl.draw()
            if event.key in ['s', 'S']:
                axs = self.__select_axes(ax, "S", event.xdata)
                for axi in axs: axi.axvline(event.xdata, picker=5)
                mpl.draw()
            if event.key in ['x', 'X']:
                if self.__selected_event != None:
                    self.__select_remove_axes(ax, self.__selected_event)
                    mpl.draw()
                self.__selected_event = None

        def on_pick(event):
            self.__selected_event = event.artist
        
        fig.canvas.setFocusPolicy( QtCore.Qt.ClickFocus )
        fig.canvas.setFocus()
        fig.canvas.mpl_connect('key_press_event', on_key)
        fig.canvas.mpl_connect('pick_event', on_pick)

    def __select_axes(self, ax, phase, xdata):
        ax_collect = []
        ax_text = ax._children[1].get_text().split('.')
        axs = self.tab_waveplots.widgetCanvas.mpl.axes.figure.axes
        for row, axi in zip(self.__plot_rows, axs):
            axi_text = axi._children[1].get_text().split('.')
            if ax_text[0:3] == axi_text[0:3]:
                ax_collect.append(axi)
        df = self.__phase_df
        df.loc[(df["network"] == ax_text[0]) &
               (df["station"] == ax_text[1]) &
               (df["location"] == ax_text[2]), phase] = str(ob.UTCDateTime(mpl.dates.num2date(xdata)))
        self.__table_phase_model = TableModel(df)
        self.table_phase.setModel(self.__table_phase_model)
        return ax_collect
    
    def __select_remove_axes(self, ax, event):
        ax_text = ax._children[1].get_text().split('.')
        x = None
        for i, ev in enumerate(ax._children):
            if ev == event:
                x = i
        axs = self.tab_waveplots.widgetCanvas.mpl.axes.figure.axes
        for row, axi in zip(self.__plot_rows, axs):
            axi_text = axi._children[1].get_text().split('.')
            if ax_text[0:3] == axi_text[0:3]:
                axi._children[x].remove()
        
    
    def __apply_distance_to_waves(self):
        self.__worker_progress("getting distances  . . .")
        self.data["selected waveforms"] = None

        if self.data["waveforms"] != None:
            g = Geod(ellps=self.configs["geod reference"])
            evlon, evlat = self.data["event coordinate"]

            selected_traces = []
            starttimes = []
            for tr in self.data["waveforms"]:
                net = tr.stats.network
                stat = tr.stats.station
                inv_sel = self.data["stations"].select(network=net, station=stat)
                if len(inv_sel) != 0:
                    stlon = inv_sel[0][0]._longitude
                    stlat = inv_sel[0][0]._latitude
                    _,_,dist = g.inv(evlon,evlat,stlon,stlat)
                    tr.stats.distance = dist 
                    selected_traces.append(tr)
                    starttimes.append(tr.stats.starttime)
            
            if selected_traces != []:
                self.data["selected waveforms"] = ob.Stream(selected_traces)
                self.data["minimum starttime"] = min(starttimes)

    def __search_stations(self):
        if self.data["waveforms"] != None:

            check_station = {
                "net": [],
                "stat": [],
            }
            inv = None
            self.__worker_progress("searching station data . . .")
            for i, tr in enumerate(self.data["waveforms"]):
                net = tr.stats.network
                stat = tr.stats.station
                t1 = tr.stats.starttime
                t2 = tr.stats.endtime
                if stat not in check_station["stat"]:
                    is_pass = False
                    for cl in self.configs["selected clients"]:
                        if is_pass == True: continue
                        try:
                            client = Client(cl)
                            inv_tmp = client.get_stations(starttime=t1, endtime=t2,
                                                            network=net, station=stat, loc="*", channel="*",
                                                            level="response")
                            if inv == None:
                                inv = inv_tmp
                            else:
                                inv.extend(inv_tmp)
                            check_station["net"].append(net)
                            check_station["stat"].append(stat)

                            is_pass = True
                            self.__worker_progress(f"client: {cl}, network: {net}, station: {stat} downloaded ({int(100*(i+1)/len(self.data['waveforms']))}%)")

                        except:
                            pass
            
            self.data["stations"] = inv
    
    def __show_waveform_offsets(self):
        fig = self.tab_time_offsets.mpl.axes.figure
        fig.clf()
        if self.data["selected waveforms"] != None:
            self.__worker_progress("showing offset plots . . .")
            stsel = self.data["selected waveforms"].select(component=self.configs["show waveform component"])
            stsel.detrend()
            # stsel.filter("highpass", freq=1.0)
            stsel.plot(type='section', recordlength=None,
                        time_down=True, linewidth=.25, grid_linewidth=.25, show=False, fig=fig)
            ax = fig.axes[0]
            transform = blended_transform_factory(ax.transData, ax.transAxes)
            for tr in stsel:
                ax.text(tr.stats.distance / 1e3, 1.0, tr.stats.station, rotation=270,
                        va="bottom", ha="center", transform=transform, zorder=10)
            self.tab_time_offsets.mpl.draw()

        else:
            self._printLn2("waveforms are not found.")

    def __precondition_waveforms(self):
        if self.tree_list["Selection"][0][3].currentIndex() == 1:
            st = None
            for net in self.tree_list["Selection"][1][3].toPlainText().split(','):
                for stat in self.tree_list["Selection"][2][3].toPlainText().split(','):
                    net = net.replace(' ', '')
                    stat = stat.replace(' ', '')
                    self.__worker_progress(stat)
                    tr = self.data["waveforms"].select(network=net,
                                                station=stat,
                                                location=self.tree_list["Selection"][3][3].toPlainText(),
                                                channel=self.tree_list["Selection"][4][3].toPlainText(),
                                                component=self.tree_list["Selection"][5][3].toPlainText())
                    if st == None:
                        st = tr
                    else:
                        st += tr
            self.data["waveforms"] = st
        if self.tree_list["Precondition"][0][3].currentIndex() == 1:
            self.__worker_progress("merging data . . .")
            self.data["waveforms"].merge(method=1, interpolation_samples=-1, fill_value='interpolate')
        if self.tree_list["Precondition"][1][3].currentIndex() == 1:
            self.__worker_progress("removing mean on data . . .")
            self.data["waveforms"].detrend(type='demean')
        if self.tree_list["Precondition"][2][3].currentIndex() == 1:
            self.__worker_progress("removing simple trend on data . . .")
            self.data["waveforms"].detrend(type='simple')
        if self.tree_list["Precondition"][3][3].currentIndex() == 1:
            self.__worker_progress("removing linear trend on data . . .")
            self.data["waveforms"].detrend(type='linear')
        if self.tree_list["Precondition"][4][3].currentIndex() == 1:
            self.__worker_progress("applying taper . . .")
            self.data["waveforms"].taper(max_percentage=0.05)

    def __filtering_waveforms(self):
        if self.tree_list["Filter"][0][3].currentIndex() == 1:
            self.__worker_progress("filtering waveform data . . .")
            fmin, fmax = [None, None]
            try:
                fmin = float(self.tree_list["Filter"][1][3].toPlainText())
            except:
                fmin = None
            try:
                fmax = float(self.tree_list["Filter"][2][3].toPlainText())
            except:
                fmax = None
            if fmin != None and fmax != None:
                self.data["waveforms"].filter("bandpass", freqmin=fmin, freqmax=fmax)
            elif fmin != None and fmax == None:
                self.data["waveforms"].filter('highpass', freq=fmin)
            elif fmin == None and fmax != None:
                self.data["waveforms"].filter('lowpass', freq=fmax)
            else:
                self.__worker_progress("cannot filtering waveform data!")

    def __customize_time_offsets(self):
        fig = self.tab_time_offsets.mpl.axes.figure
        ax = fig.axes[0]
        _, xmax = ax.get_xlim()
        if self.tree_list["Time vs. Offsets"][0][3].currentIndex() == 1:
            self.__worker_progress("adding a line of origin time in Time vs. Offsets . . .")
            self.data['origin time'] = ob.UTCDateTime(self.tree_list["Event"][0][3].dateTime().toPyDateTime())
            delta_t = self.data['origin time'] - self.data['minimum starttime']
            ax.plot([0, xmax], [delta_t, delta_t], c="blue", label='origin time')

        if self.tree_list["Time vs. Offsets"][1][3].currentIndex() == 1:
            self.__worker_progress("adding a line of velocity in Time vs. Offsets . . .")
            self.data['origin time'] = ob.UTCDateTime(self.tree_list["Event"][0][3].dateTime().toPyDateTime())
            delta_t = self.data['origin time'] - self.data['minimum starttime']
            vs, vp = [None, None]
            try:
                vp = float(self.tree_list["Time vs. Offsets"][2][3].toPlainText())
            except:
                vp = None
            try:
                vs = float(self.tree_list["Time vs. Offsets"][3][3].toPlainText())
            except:
                vs = None
            if vp != None and vs != None:
                for v, c, l in zip([vp, vs], ["red", "green"], ["Vp", "Vs"]):
                    tmax = delta_t + xmax / v
                    ax.plot([0, xmax], [delta_t, tmax], c=c, label=l)
            elif vp != None and vs == None:
                tmax = delta_t + xmax / vp
                ax.plot([0, xmax], [delta_t, tmax], c = "red", label="Vp")
            elif vp == None and vs != None:
                tmax = delta_t + xmax / vs
                ax.plot([0, xmax], [delta_t, tmax], c = "green", label="Vs")
            
        ax.legend()
        self.tab_time_offsets.mpl.draw()

    def _modify_waveforms(self):
        if self.tree_list["Waveform Location"][1][3].currentIndex() == 1:
            self.__worker_progress("reading waveform data . . .")
            self.worker.progress_int.emit(10)
                
            fileNames = self.tree_list['Waveform Location'][0][3].text.toPlainText()
            self.__worker_progress(fileNames)
            try:
                for i, fn in enumerate(fileNames.split('\n')):
                    if i == 0:
                        self.data["waveforms"] = ob.read(fn)
                    else:
                        self.data["waveforms"] += ob.read(fn)

                self.__base_waveforms = self.data["waveforms"].copy()
            except:
                self.__worker_progress("The data cannot be load.")
                self.data["waveforms"] = None
        else:
            self.data["waveforms"] = self.__base_waveforms.copy()

        if self.data["waveforms"] != None:
            self.__precondition_waveforms()
            self.worker.progress_int.emit(20)

            self.__filtering_waveforms()
            self.worker.progress_int.emit(40)

            self.__set_table_waves()
            self.worker.progress_int.emit(60)

            if self.tree_list["Plot Options"][0][3].currentIndex() == 1:
                self.__worker_progress("plotting waveform data . . .")
                self.__show_waveplots(self.tab_waveplots.widgetCanvas.mpl, self.data["waveforms"])
                self.worker.progress_int.emit(80)

            if self.tree_list["Stations"][0][3].currentIndex() == 1:
                self.__search_stations()
            else:
                self.__worker_progress("reading station data . . .")
                fileNames = self.tree_list['Stations'][1][3].text.toPlainText()
                self.__worker_progress(fileNames)
                if fileNames != "":
                    try:
                        for i, fn in enumerate(fileNames.split('\n')):
                            if i == 0:
                                self.data["stations"] = ob.read_inventory(fn)
                            else:
                                self.data["stations"].extend(ob.read_inventory(fn))
                    except:
                        self.__worker_progress("The stations cannot be load.")
                        self.data["stations"] = None

            self.worker.progress_int.emit(90)

            if self.tree_list["Plot Options"][1][3].currentIndex() == 1:
                if self.tree_list["Stations"][2][3].currentIndex() == 1:
                    self.data["event coordinate"] = [None, None]
                    try:
                        evlon = float(self.tree_list["Event"][1][3].toPlainText())
                        evlat = float(self.tree_list["Event"][2][3].toPlainText())
                        self.data["event coordinate"] = [evlon, evlat]
                        self.__worker_progress(f"a selected event (lon, lat): {self.data['event coordinate']}")
                    except:
                        pass
                    
                    if self.data["event coordinate"] != [None, None]:
                        self.__apply_distance_to_waves()
                        self.__show_waveform_offsets()
                        self.__customize_time_offsets()
                    else:
                        self.__worker_progress("the event coordinate is not found!")
    
    def __worker_progress(self, txt):
        if self.worker != None:
            self.worker.progress.emit(txt)

    def _on_btn_saveas_waveforms_clicked(self):
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Waveforms", "", "MSEED Files (*.mseed)")
        if fileName:
            if self.data["waveforms"] != None:
                self.data["waveforms"].write(fileName, format="MSEED")
                self._printLn2(f"saving waveform data to {fileName}")

    def _on_btn_saveas_stationxml_clicked(self):
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Station XML", "", "XML Files (*.xml)")
        if fileName:
            if self.data["stations"] != None:
                self.data["stations"].write(fileName, format="STATIONXML")
                self._printLn2(f"saving station data to {fileName}")