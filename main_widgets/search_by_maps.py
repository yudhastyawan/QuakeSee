from PyQt5 import QtWidgets, uic, QtCore
import sys
import geopandas as gpd
import obspy as ob
from obspy.clients.fdsn.header import URL_MAPPINGS
from obspy.clients.fdsn.client import Client
from obspy.clients.fdsn import RoutingClient
from pyproj import Geod
from matplotlib.transforms import blended_transform_factory

from libs.select_from_collection import SelectFromCollection
from libs.commons import Worker

class SearchByMaps(QtWidgets.QWidget):
    def __init__(self, parent = None):
        QtWidgets.QWidget.__init__(self, parent)

        #Load the UI Page
        uic.loadUi('./ui/search_by_maps.ui', self)

        # variables
        self.configs = {
            "base clients": list(URL_MAPPINGS.keys()),
            "selected clients": list(URL_MAPPINGS.keys()),
            "client events": "GFZ",
            "Mmin": 4,
            "waveform time": [-2,200],
            "network filter": "*",
            "station filter": "*",
            # "search filter": ["?H?", "[BHE]*"],
            "channel filter": "BH?,EH?,HH?",
            "geod reference": 'WGS84',
            "show waveform component": 'Z',
        }

        # configs base
        self.configs_base = self.configs.copy()

        self.data = {
            "events": None,
            "selected event": None,
            "stations": None,
            "selected stations": None,
            "waveforms": None
        }

        self._print = lambda x: self.py_console._append_plain_text(x, True)
        self._printLn = lambda x: self._print(x + "\n")
        self._printLn2 = lambda x: self._print("\n" + x + "\n")

        # temporary variables
        self.__pass_inv = None
        self.stat_txts = []
        self.accepted_bulks = []


        # initial state
        self.cv_distance.mpl.axes.figure.clf()

        kernel_dict = {
            "_map":self,
            "map_configs":self.configs,
            "map_data":self.data,
            "map_configs_reset":self.reset_configs
        }

        self._push_kernel = lambda: self.py_console.push_kernel(kernel_dict)

        self.ind_ev = 0
        def get_ind(mpl):
            self.ind_ev = mpl.ind
            self.data["selected event"] = self.data["events"][self.ind_ev]
            self._printLn2(self.data["selected event"].__str__())
        
        self.thread = None
        self.worker = None

        self.mpl_map_reset(self.mpl_select_map.mpl)
        self.mpl_select_map_plot.mpl.communicate.sig[int].connect(
            lambda: self.show_events_in_mpl_2(self.mpl_select_map_plot.mpl))
        self.mpl_select_map_plot.mpl.communicate.sig[int].connect(
            lambda: get_ind(self.mpl_select_map_plot.mpl))
        
    def reset_configs(self):
        for key in self.configs.keys():
            self.configs[key] = self.configs_base[key]

    def _on_btn_map_reset(self):
        self.mpl_map_reset(self.mpl_select_map.mpl)

    def mpl_map_reset(self, mpl):
        def get_ind(mpl):
            self.ind_ev = mpl.ind
            self.data["selected event"] = self.data["events"][self.ind_ev]
            self._printLn2(self.data["selected event"].__str__())

        mpl.axes.cla()
        self.draw_basemap(mpl)
        mpl._activate_rectangle()
        mpl.communicate.sig[int].connect(
            lambda: self.show_events_in_mpl_2(mpl))
        mpl.communicate.sig[int].connect(
            lambda: get_ind(mpl))

    def draw_basemap(self, mpl):
        gdf_map = gpd.read_file('./coastlines/ne_110m_land.shp')
        ax = mpl.axes
        gdf_map.plot(color='lightgrey', edgecolor='black', linewidth=1, ax=ax, clip_on=False)
        mpl.axes.tick_params(axis="y",direction="in", pad=-22)
        mpl.axes.tick_params(axis="x",direction="in", pad=-15)
        mpl.axes.figure.tight_layout(pad=0, w_pad=0, h_pad=0)
        mpl.axes.margins(0)
        mpl.draw()

    def run_kernel(self):
        self.py_console.run_kernel(self.py_editor.toPlainText())
        self.tab_code.setCurrentIndex(0)

    def _show_events(self):
        if self.worker != None:
            self.worker.progress.emit("\nsearch events . . .")

        client = Client(self.configs["client events"])
        t1 = ob.UTCDateTime(self.datetime_start.dateTime().toPyDateTime())
        t2 = ob.UTCDateTime(self.datetime_end.dateTime().toPyDateTime())
        (minlon, maxlon), (minlat, maxlat) = self.mpl_select_map.mpl.data
        try:
            self.data["events"] = client.get_events(starttime=t1, endtime=t2, minmagnitude=self.configs["Mmin"], 
                                    minlongitude=minlon, maxlongitude=maxlon, minlatitude=minlat, maxlatitude=maxlat)
            x = []
            y = []
            m = []
            t = []
            for event in self.data["events"]:
                x.append(event.origins[0].longitude)
                y.append(event.origins[0].latitude)
                m.append(event.magnitudes[0].mag)
                t.append(event.origins[0].time.matplotlib_date)
            
            if self.worker != None:
                self.worker.progress.emit("plotting . . .")

            ax = self.mpl_select_map.mpl.axes
            ax.plot(x, y, 'ro', picker=10, clip_on=False)
            self.mpl_select_map.mpl.draw()

            self.mpl_select_map_plot.mpl.axes.cla()
            ax = self.mpl_select_map_plot.mpl.axes
            ax.plot(t, m, 'ro', picker=10, clip_on=False)
            ax.xaxis_date()
            ax.figure.autofmt_xdate()
            ax.set_ylabel("Magnitude")
            ax.set_xlabel("Time")
            self.mpl_select_map_plot.mpl.draw()
        except:
            if self.worker != None:
                self.worker.progress.emit("error during the process!")
        # print(self.data["events"])

    def _on_btn_show_events_clicked(self):
        self.thread = QtCore.QThread()
        self.worker = Worker(self._show_events)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(lambda: self._printLn("finished!"))
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.progress[str].connect(self._printLn)
        self.thread.start()

        # Final resets
        self.btn_showevents.setEnabled(False)
        self.thread.finished.connect(
            lambda: self.btn_showevents.setEnabled(True)
        )
        self.thread.finished.connect(lambda: self.btn_rectangle.setChecked(False))
        
    def _on_btn_show_stations_clicked(self):
        self.thread = QtCore.QThread()
        self.worker = Worker(self._show_stations)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(lambda: self._printLn("finished!"))
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.progress[str].connect(self._printLn)
        self.thread.start()

        # Final resets
        self.btn_showstations.setEnabled(False)
        self.thread.finished.connect(
            lambda: self.btn_showstations.setEnabled(True)
        )
        self.thread.finished.connect(lambda: self.btn_rectangle_2.setChecked(False))

    def _show_stations(self):
        client = RoutingClient("iris-federator")

        t1 = ob.UTCDateTime(self.datetime_start.dateTime().toPyDateTime())
        t2 = ob.UTCDateTime(self.datetime_end.dateTime().toPyDateTime())
        (minlon, maxlon), (minlat, maxlat) = self.mpl_select_map_2.mpl.data

        if self.worker != None:
            self.worker.progress.emit("\nsearch stations . . .")

        self.data["stations"] = client.get_stations(network=self.configs["network filter"], channel=self.configs["channel filter"], starttime=t1,
                                    endtime=t2,level="response",
                                    minlongitude=minlon, maxlongitude=maxlon, minlatitude=minlat, maxlatitude=maxlat)
        # self.data["stations"] = self.data["stations"].select(network=self.configs["network filter"], channel=self.configs["channel filter"][1])
        self.data["selected stations"] = self.data["stations"]
        
        x = []
        y = []
        self.__pass_inv = dict()
        __n = 0
        for i, net in enumerate(self.data["stations"]):
            for j, stat in enumerate(net):
                x.append(stat._longitude)
                y.append(stat._latitude)
                self.__pass_inv[f"{__n}"] = [i,j]
                __n += 1


        ax = self.mpl_select_map_2.mpl.axes

        self.stat_points = ax.scatter(x, y, c='k', s=80, marker='^', clip_on=False)
        if self.worker != None:
            self.worker.progress.emit("data being plotted . . .")

        self.stat_selector = SelectFromCollection(ax, self.stat_points)
        self.mpl_select_map_2.mpl.draw()
    
    def show_events_in_mpl_2(self, mpl):
        self.mpl_select_map_2.mpl.axes.cla()
        self.draw_basemap(self.mpl_select_map_2.mpl)
        self.mpl_select_map_2.mpl._activate_rectangle()
        # gdf_map = gpd.read_file('./coastlines/ne_110m_land.shp')
        ax = self.mpl_select_map_2.mpl.axes
        # gdf_map.plot(ax=ax, clip_on=False)
        idx = mpl.ind
        ax.plot(self.data["events"][idx].origins[0].longitude,
                self.data["events"][idx].origins[0].latitude,
                'ro', clip_on=False)
        self.mpl_select_map_2.mpl.draw()

    def _select_stations(self, bool):
        if self.stat_txts != []:
            for txt in self.stat_txts:
                txt.remove()
            self.mpl_select_map_2.mpl.draw()
            self.stat_txts = []

        if bool == True:
            ax = self.mpl_select_map_2.mpl.axes
            self.stat_selector = SelectFromCollection(ax, self.stat_points)
            self.stat_selector.communicate.sigEmpty.connect(self.__select_stations_by_indices)

        else:
            self.stat_selector.disconnect()
            self.mpl_select_map_2.mpl.draw()

    def __select_stations_by_indices(self):
        self.data["selected stations"] = None
        for __n, idx in enumerate(self.stat_selector.ind):
            i, j = self.__pass_inv[f"{idx}"]
            inv_i = self.data["stations"][i][j]
            net = self.data["stations"][i]._code
            st = inv_i._code
            if __n == 0:
                self.data["selected stations"] = self.data["stations"].select(network=net, station=st)
            else:
                self.data["selected stations"].extend(self.data["stations"].select(network=net, station=st))

    def _on_btn_get_waveforms_clicked(self):
        self.thread = QtCore.QThread()
        self.worker = Worker(self._get_waveforms)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(lambda: self._printLn("finished!"))
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.progress.connect(self._printLn)
        self.thread.start()

        self.btn_getwaves.setEnabled(False)
        self.thread.finished.connect(
            lambda: self.btn_getwaves.setEnabled(True)
        )

    def _get_waveforms(self):
        g = Geod(ellps=self.configs["geod reference"])

        otime = self.data["selected event"].origins[0].time
        t1 = otime + self.configs["waveform time"][0]
        t2 = otime + self.configs["waveform time"][1]

        evlon = self.data["selected event"].origins[0].longitude
        evlat = self.data["selected event"].origins[0].latitude

        bulk = []
        for i, net in enumerate(self.data["selected stations"]):
            for j, stat in enumerate(net):
                net_code = net._code
                st_code = stat._code
                lon = stat._longitude
                lat = stat._latitude
                _,_,dist = g.inv(evlon,evlat,lon,lat)
                bulk.append((net_code,st_code, "*", self.configs["channel filter"], t1, t2, dist, lon, lat))

        if self.worker != None:
            self.worker.progress.emit("\nsearch available waveforms . . .")
        self.data["waveforms"] = None
        self.accepted_bulks = []
        nn = 0
        for i_bl, bl in enumerate(bulk):
            is_pass = False
            for cl in self.configs["selected clients"]:
                if is_pass == True: continue
                try:
                    client = Client(cl)
                    st = client.get_waveforms(network=bl[0], station=bl[1], location=bl[2], channel=bl[3], 
                                              starttime=bl[4], endtime=bl[5])
                    # st = st.select(channel=self.configs["channel filter"][1])
                    if (len(st) != 0):
                        for tr in st:
                            tr.stats.distance = bl[6]
                        if nn == 0:
                            self.data["waveforms"] = st
                        else:
                            self.data["waveforms"] += st
                        nn += 1
                        if self.worker != None:
                            self.worker.progress.emit(f"net: {bl[0]}, st: {bl[1]}, client: {cl}, downloaded ({int(100*(i_bl+1)/len(bulk))}%)")
                        self.accepted_bulks.append(bl)
                        is_pass = True
                except:
                    pass

    def _show_waveforms(self):
        fig = self.cv_distance.mpl.axes.figure
        fig.clf()
        if self.data["waveforms"] != None:
            stsel = self.data["waveforms"].select(component=self.configs["show waveform component"])
            stsel.detrend()
            # stsel.filter("highpass", freq=1.0)
            stsel.plot(type='section', recordlength=None,
                        time_down=True, linewidth=.25, grid_linewidth=.25, show=False, fig=fig)
            ax = fig.axes[0]
            transform = blended_transform_factory(ax.transData, ax.transAxes)
            for tr in stsel:
                ax.text(tr.stats.distance / 1e3, 1.0, tr.stats.station, rotation=270,
                        va="bottom", ha="center", transform=transform, zorder=10)
            self.cv_distance.mpl.draw()

            if self.stat_txts != []:
                for txt in self.stat_txts:
                    txt.remove()
                self.mpl_select_map_2.mpl.draw()
                self.stat_txts = []

            ax = self.mpl_select_map_2.mpl.axes
            for bl in self.accepted_bulks:
                self.stat_txts.append(ax.text(bl[7], bl[8], bl[1], clip_on=False))
            self.mpl_select_map_2.mpl.draw()
        else:
            self._printLn2("waveforms are not found.")

    def _save_stations(self):
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Stations", "", "XML Files (*.xml)")
        if fileName:
            if self.data["selected stations"] != None:
                self.data["selected stations"].write(fileName, format="STATIONXML")
                self._printLn2(f"saving station data to {fileName}")
    
    def _save_waveforms(self):
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Waveforms", "", "MSEED Files (*.mseed)")
        if fileName:
            if self.data["waveforms"] != None:
                self.data["waveforms"].write(fileName, format="MSEED")
                self._printLn2(f"saving waveform data to {fileName}")


def main():
    app = QtWidgets.QApplication(sys.argv)
    main = SearchByMaps()
    main.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()