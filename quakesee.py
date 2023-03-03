from PyQt5 import QtWidgets, uic, QtCore
import sys
import geopandas as gpd
import obspy as ob
import numpy as np
from obspy.clients.fdsn.client import Client
from obspy.clients.fdsn import RoutingClient
from pyproj import Geod
from matplotlib.transforms import blended_transform_factory

from libs.selectfromcollection import SelectFromCollection

class Worker(QtCore.QObject):
    finished = QtCore.pyqtSignal()
    progress = QtCore.pyqtSignal(str)

    def __init__(self, func, parent = None):
        QtCore.QObject.__init__(self, parent)
        self.func = func
    
    def run(self):
        self.func()
        self.finished.emit()

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        #Load the UI Page
        uic.loadUi('mainwindow.ui', self)

        # variables
        self.configs = {
            "client events": "GFZ",
            "Mmin": 4,
            "waveform time": [2,200],
            "search filter": ["?H?", "[BHE]*"],
            "geod reference": 'WGS84',
            "show waveform component": 'Z',
        }

        self.data = {
            "events": None,
            "selected event": None,
            "stations": None,
            "selected stations": None,
            "waveforms": None
        }

        # temporary variables
        self.__pass_inv = None
        self.stat_txts = []
        self.accepted_bulks = []


        # initial state
        self.cv_distance.mpl.axes.figure.clf()

        kernel_dict = {
            "self":self
        }

        self.py_console.push_kernel(kernel_dict)

        self.ind_ev = 0
        def get_ind(mpl):
            self.ind_ev = mpl.ind
        
        self.thread = None
        self.worker = None

        self.mpl_map_reset(self.mpl_select_map.mpl)
        self.mpl_select_map_plot.mpl.communicate.sig[int].connect(
            lambda: self.show_events_in_mpl_2(self.mpl_select_map_plot.mpl))
        self.mpl_select_map_plot.mpl.communicate.sig[int].connect(
            lambda: get_ind(self.mpl_select_map_plot.mpl))

    def on_btn_map_reset(self):
        self.mpl_map_reset(self.mpl_select_map.mpl)

    def mpl_map_reset(self, mpl):
        def get_ind(mpl):
            self.ind_ev = mpl.ind

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
        mpl.draw()

    def run_kernel(self):
        self.py_console.run_kernel(self.py_editor.toPlainText())
        self.tab_code.setCurrentIndex(0)

    def show_events(self):
        if self.worker != None:
            self.worker.progress.emit("search events . . .\n")

        client = Client(self.configs["client events"])
        t1 = ob.UTCDateTime(self.datetime_start.dateTime().toPyDateTime())
        t2 = ob.UTCDateTime(self.datetime_end.dateTime().toPyDateTime())
        (minlon, maxlon), (minlat, maxlat) = self.mpl_select_map.mpl.data
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
            self.worker.progress.emit("plotting . . .\n")

        ax = self.mpl_select_map.mpl.axes
        ax.plot(x, y, 'ro', picker=10, clip_on=False)
        self.mpl_select_map.mpl.draw()

        self.mpl_select_map_plot.mpl.axes.cla()
        ax = self.mpl_select_map_plot.mpl.axes
        ax.plot(t, m, 'ro', picker=10, clip_on=False)
        ax.xaxis_date()
        ax.figure.autofmt_xdate()
        self.mpl_select_map_plot.mpl.draw()
        # print(self.data["events"])

    def on_btn_show_events_clicked(self):
        self.thread = QtCore.QThread()
        self.worker = Worker(self.show_events)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(lambda: self.py_console._append_plain_text("finished!\n", True))
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.progress[str].connect(lambda x: self.py_console._append_plain_text(x, True))
        self.thread.start()

        # Final resets
        self.btn_showevents.setEnabled(False)
        self.thread.finished.connect(
            lambda: self.btn_showevents.setEnabled(True)
        )
        self.thread.finished.connect(lambda: self.btn_rectangle.setChecked(False))
        
    def on_btn_show_stations_clicked(self):
        self.thread = QtCore.QThread()
        self.worker = Worker(self.show_stations)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(lambda: self.py_console._append_plain_text("finished!\n", True))
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.progress[str].connect(lambda x: self.py_console._append_plain_text(x, True))
        self.thread.start()

        # Final resets
        self.btn_showstations.setEnabled(False)
        self.thread.finished.connect(
            lambda: self.btn_showstations.setEnabled(True)
        )
        self.thread.finished.connect(lambda: self.btn_rectangle_2.setChecked(False))

    def show_stations(self):
        client = RoutingClient("iris-federator")

        t1 = ob.UTCDateTime(self.datetime_start.dateTime().toPyDateTime())
        t2 = ob.UTCDateTime(self.datetime_end.dateTime().toPyDateTime())
        (minlon, maxlon), (minlat, maxlat) = self.mpl_select_map_2.mpl.data

        if self.worker != None:
            self.worker.progress.emit("search stations . . .\n")

        self.data["stations"] = client.get_stations(channel=self.configs["search filter"][0], starttime=t1,
                                    endtime=t2,level="response",
                                    minlongitude=minlon, maxlongitude=maxlon, minlatitude=minlat, maxlatitude=maxlat)
        self.data["stations"] = self.data["stations"].select(channel=self.configs["search filter"][1])
        
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
            self.worker.progress.emit("data being plotted . . .\n")

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

    def select_stations(self, bool):
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

    def on_btn_get_waveforms_clicked(self):
        self.thread = QtCore.QThread()
        self.worker = Worker(self.get_waveforms)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(lambda: self.py_console._append_plain_text("finished!\n", True))
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.progress.connect(lambda x: self.py_console._append_plain_text(x, True))
        self.thread.start()

        self.btn_getwaves.setEnabled(False)
        self.thread.finished.connect(
            lambda: self.btn_getwaves.setEnabled(True)
        )

    def get_waveforms(self):
        g = Geod(ellps=self.configs["geod reference"])
        idx_event = self.ind_ev
        idx_stats = self.stat_selector.ind

        self.data["selected event"] = self.data["events"][idx_event]
        otime = self.data["selected event"].origins[0].time
        t1 = otime - self.configs["waveform time"][0]
        t2 = otime + self.configs["waveform time"][1]

        evlon = self.data["selected event"].origins[0].longitude
        evlat = self.data["selected event"].origins[0].latitude

        bulk = []
        for idx in idx_stats:
            i, j = self.__pass_inv[f"{idx}"]
            inv_i = self.data["stations"][i][j]
            net = self.data["stations"][i]._code
            st = inv_i._code
            lon = inv_i._longitude
            lat = inv_i._latitude
            _,_,dist = g.inv(evlon,evlat,lon,lat)
            bulk.append((net,st, "*", self.configs["search filter"][0], t1, t2, dist, lon, lat, i, j))

        # print(bulk)
        if self.worker != None:
            self.worker.progress.emit("search available waveforms . . .\n")
        self.data["waveforms"] = None
        self.accepted_bulks = []
        nn = 0
        for i_bl, bl in enumerate(bulk):
            is_pass = False
            for cl in ['AUSPASS', 'BGR', 'EIDA', 'ETH', 'EMSC', 'GEONET', 
                       'GEOFON', 'GFZ', 'ICGC', 'IESDMC', 'INGV', 'IPGP', 
                       'IRIS', 'IRISPH5', 'ISC', 'KNMI', 'KOERI', 'LMU', 
                       'NCEDC', 'NIEP', 'NOA', 'ODC', 'ORFEUS', 'RESIF', 
                       'RESIFPH5', 'RASPISHAKE', 'SCEDC', 'TEXNET', 'UIB-NORSAR', 
                       'USGS', 'USP']:
                if is_pass == True: continue
                try:
                    client = Client(cl)
                    st = client.get_waveforms(network=bl[0], station=bl[1], location=bl[2], channel=bl[3], 
                                              starttime=bl[4], endtime=bl[5])
                    st = st.select(channel=self.configs["search filter"][1])
                    if (len(st) != 0):
                        for tr in st:
                            tr.stats.distance = bl[6]
                        if nn == 0:
                            self.data["waveforms"] = st
                        else:
                            self.data["waveforms"] += st
                        nn += 1
                        if self.worker != None:
                            self.worker.progress.emit(f"net: {bl[0]}, st: {bl[1]}, client: {cl}, downloaded ({int(100*(i_bl+1)/len(bulk))}%)\n")
                        self.accepted_bulks.append(bl)
                        is_pass = True
                except:
                    pass

    def show_waveforms(self):
        fig = self.cv_distance.mpl.axes.figure
        fig.clf()
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


def main():
    app = QtWidgets.QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()