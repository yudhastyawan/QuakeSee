"""
Author: Yudha Styawan
File: search_by_maps.py
"""

from PyQt5 import QtWidgets, uic, QtCore
import sys
import os
import numpy as np
import geopandas as gpd
import pandas as pd
import obspy as ob
from obspy.clients.fdsn.header import URL_MAPPINGS
from obspy.clients.fdsn.client import Client
from obspy.clients.fdsn import RoutingClient
from pyproj import Geod
from matplotlib.transforms import blended_transform_factory
from matplotlib.patches import Circle

from libs.select_from_collection import SelectFromCollection
from widgets.messagebox import MBox, MBoxLbl
from libs.commons import Worker
from libs.utils import TableModel
import matplotlib.pyplot as plt
from obspy.taup import TauPyModel, plot_travel_times
from widgets.mplcanvas import MplCanvasBaseWithToolbar

class SearchByMaps(QtWidgets.QWidget):
    """
    Searching events, stations, and waveforms available publicly on the providers
    """
    def __init__(self, parent = None):
        QtWidgets.QWidget.__init__(self, parent)

        #Load the UI Page
        uic.loadUi('./ui/search_by_maps.ui', self)

        # configurations
        # - base clients    : available providers
        # - selected clients: providers used for searching stations and waveforms
        # - client events   : a provider used for searching events
        # - Mmin            : Minimum magnitude used for limiting events
        # - waveform time   : a list consists of 2 elements, the relative time in seconds before
        #                     and after origin time, used for limiting waveforms
        # - network filter  : network used for limiting stations. Accept UNIX wildcard, 
        #                     such as *, ?, and [], except {}. Accept multiple conditions separated by
        #                     comma
        # - station filter  : station used for limiting station codes. Using the same condition as network
        #                     filter
        # - channel filter  : channel used for limiting stations. Using the same condition as network
        #                     filter
        # - geod reference  : geodetic reference used for converting lonlat to meters, vice versa.
        # - show waveform component: the component used for the time vs offset plots.
        # - (not used) search filter   : ["?H?", "[BHE]*"]
        url_keys = list(URL_MAPPINGS.keys())
        url_keys.remove('IRISPH5')
        cl_ev_keys = ["AUSPASS", "BGR", "EIDA", "EMSC", "ETH", "GEOFON", "GEONET", 
                      "GFZ", "ICGC", "IESDMC", "INGV", "IPGP", "IRIS", "IRISPH5", 
                      "ISC", "KNMI", "KOERI", "LMU", "NCEDC", "NIEP", "NOA", "ODC", 
                      "ORFEUS", "RASPISHAKE", "RESIF", "RESIFPH5", "SCEDC", "TEXNET", 
                      "UIB-NORSAR", "USGS", "USP"]
        self.configs = {
            "base clients"            : url_keys,
            "selected clients"        : url_keys,
            "client events"           : "GFZ",
            "available client events" : cl_ev_keys,
            "Mmin"                    : 4,
            "Mmax"                    : None,
            "waveform time"           : [-2,400],
            "network filter"          : "*",
            "station filter"          : "*",
            "channel filter"          : "BH?,EH?,HH?",
            "geod reference"          : 'WGS84',
            "show waveform component" : 'Z',
            "includeallorigins"       : False,
            "includeallmagnitudes"    : False,
            "includearrivals"         : False,
            "mindepth"                : None,
            "maxdepth"                : None
        }

        # configs base
        # - used for the back-up configs while the configs need to be reset.
        self.configs_base = self.configs.copy()

        # data
        # - events            : the collection of events after searching
        # - selected event    : a particular event used for searching stations and waveforms
        # - stations          : the collection of events for a "selected event"
        # - selected stations : used for searching waveforms
        # - waveforms         : the collection of waveforms for a "selected event" and "selected stations"
        self.data = {
            "events"            : None,
            "selected event"    : None,
            "stations"          : None,
            "selected stations" : None,
            "waveforms"         : None
        }

        # print to console
        self._print    = lambda x: self.py_console._append_plain_text(x, True)
        self._printLn  = lambda x: self._print(x + "\n")
        self._printLn2 = lambda x: self._print("\n" + x + "\n")

        # temporary variables
        self.__pass_inv     = None
        self.__map_df       = None
        self.stat_txts      = []
        self.accepted_bulks = []
        self._circ          = None


        # initial state
        self.cv_distance.mpl.axes.figure.clf()
        self.thread = None
        self.worker = None

        # kernel
        # - _map: notably used for debugging.
        # - map_configs: a "call" name for showing all configurations in console.
        # - map_data: a "call" name for showing all data info in console
        # - map_configs_reset: a function for reset the configs. But call it by "map_configs_reset()"
        kernel_dict = {
            "_map"              :self,
            "map_configs"       :self.configs,
            "map_data"          :self.data,
            "map_configs_reset" :self.reset_configs,
            "check_tt"          :self.check_tt,
            "check_ray"         :self.check_ray,
            "check_plot_tt"     :self.check_plot_tt,
            "set_twmin"         :self.set_twmin,
            "set_twmax"         :self.set_twmax
        }

        # a function to push kernel to console
        self._push_kernel = lambda: self.py_console.push_kernel(kernel_dict)

        # a local function to get an index of the selected event
        self.ind_ev = 0
        def get_ind(mpl):
            self.ind_ev = mpl.ind
            self.data["selected event"] = self.data["events"][self.ind_ev]
            self._printLn2(self.data["selected event"].__str__())

        # reset map
        self.mpl_map_reset(self.mpl_select_map.mpl)

        # signal/slot while clicking a selected event
        self.mpl_select_map_plot.mpl.communicate.sig[int].connect(
            lambda: self.show_events_in_mpl_2(self.mpl_select_map_plot.mpl))
        self.mpl_select_map_plot.mpl.communicate.sig[int].connect(
            lambda: get_ind(self.mpl_select_map_plot.mpl))
        
        # set datetime
        self.datetime_start.setDateTime(QtCore.QDateTime.currentDateTime().addSecs(- 5 * 60).addDays(- 1))
        self.datetime_end.setDateTime(QtCore.QDateTime.currentDateTime().addSecs(- 5 * 60))

    def check_tt(self, depth_km, dist_deg, phases_list, model="iasp91"):
        model = TauPyModel(model=model)
        arrivals = model.get_travel_times(source_depth_in_km=depth_km,
                                  distance_in_degree=dist_deg,
                                  phase_list=phases_list)
        self._printLn(str(arrivals))

    def check_ray(self, depth_km, dist_deg, phases_list, plot_type='spherical', model="iasp91", indicate_wave_type=True):
        model = TauPyModel(model=model)
        arrivals = model.get_ray_paths(source_depth_in_km=depth_km,
                                  distance_in_degree=dist_deg,
                                  phase_list=phases_list)
        
        self._ray_wid = MplCanvasBaseWithToolbar()
        self._ray_wid.setWindowTitle("Ray Paths")
        ax = self._ray_wid.mpl.axes
        ax.figure.clf()
        arrivals.plot_rays(plot_type=plot_type, indicate_wave_type=indicate_wave_type, fig=ax.figure, show=False)
        self._ray_wid.show()

    def check_plot_tt(self, source_depth_km, minor=False, **kwargs):
        """
        https://docs.obspy.org/packages/autogen/obspy.taup.tau.plot_travel_times.html
        """
        self._ray_wid = MplCanvasBaseWithToolbar()
        self._ray_wid.setWindowTitle("Travel Times")
        ax = self._ray_wid.mpl.axes
        fig = ax.figure
        fig.clf()
        ax = plot_travel_times(source_depth_km, fig=fig, show=False, **kwargs)

        # add minor ticks
        if minor:
            ax.grid(visible=True, which='minor')
            ax.minorticks_on()
            ax.grid(visible=True, which='major', linewidth=2)
            ax.figure.canvas.draw()

        self._ray_wid.show()
        return ax

    def set_twmin(self, t_sec):
        self.configs["waveform time"][0] = t_sec

    def set_twmax(self, t_sec):
        self.configs["waveform time"][1] = t_sec
        
    def reset_configs(self):
        """
        reset the configs to default
        """
        for key in self.configs.keys():
            self.configs[key] = self.configs_base[key]

    def _on_btn_map_reset(self):
        """
        reset the map to a blank canvas (used for button)
        """
        self.mpl_map_reset(self.mpl_select_map.mpl)

    def mpl_map_reset(self, mpl):
        """
        reset the map to a blank canvas
        """
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
        """
        draw the world basemap (low resolution) in the map
        """
        gdf_map = gpd.read_file('./coastlines/ne_110m_land.shp')
        ax = mpl.axes
        gdf_map.plot(color='lightgrey', edgecolor='black', linewidth=1, ax=ax, clip_on=False)
        mpl.axes.tick_params(axis="y",direction="in", pad=-22)
        mpl.axes.tick_params(axis="x",direction="in", pad=-15)
        mpl.axes.figure.tight_layout(pad=0, w_pad=0, h_pad=0)
        mpl.axes.margins(0)
        mpl.draw()

    def run_kernel(self):
        """
        running a python script from the editor on the console
        """
        self.py_console.run_kernel(self.py_editor.toPlainText())
        self.tab_code.setCurrentIndex(0)

    def _show_events(self):
        """
        showing events based on the formed rectangle
        """
        if self.worker != None:
            self.worker.progress.emit("\nsearch events . . .")

        # t1 and t2 as the time limitation (min and max)
        t1 = ob.UTCDateTime(self.datetime_start.dateTime().toPyDateTime())
        t2 = ob.UTCDateTime(self.datetime_end.dateTime().toPyDateTime())

        # lon and lat from the rectangle
        (minlon, maxlon), (minlat, maxlat) = self.mpl_select_map.mpl.data

        try:
            client = Client(self.configs["client events"])
            self.data["events"] = client.get_events(
                starttime=t1, endtime=t2, 
                minmagnitude=self.configs["Mmin"], maxmagnitude=self.configs["Mmax"],
                includeallorigins=self.configs["includeallorigins"],
                includeallmagnitudes=self.configs["includeallmagnitudes"],
                includearrivals=self.configs["includearrivals"],
                mindepth=self.configs["mindepth"], maxdepth=self.configs["maxdepth"],
                minlongitude=minlon, maxlongitude=maxlon, 
                minlatitude=minlat, maxlatitude=maxlat)
            x = []
            y = []
            m = []
            mt = []
            d = []
            t = []
            tutc = []
            a = []
            for event in self.data["events"]:
                x.append(event.origins[0].longitude)
                y.append(event.origins[0].latitude)
                m.append(event.magnitudes[0].mag)
                mt.append(event.magnitudes[0].magnitude_type)
                t.append(event.origins[0].time.matplotlib_date)
                d.append(event.origins[0].depth/1000)
                tutc.append(str(event.origins[0].time))
                a.append(event.event_descriptions[0].text)
            
            if self.worker != None:
                self.worker.progress.emit("plotting . . .")

            # plotting events to the basemap
            ax = self.mpl_select_map.mpl.axes
            ax.plot(x, y, 'ro', picker=10, clip_on=False)
            self.mpl_select_map.mpl.draw()

            # creating a table
            if self.chk_showtable.isChecked():
                if self.worker != None:
                    self.worker.progress.emit("creating a table . . .")
                event_dict = {
                    "origin time"   :tutc,
                    "longitude"     :x, 
                    "latitude"      :y, 
                    "depth"         :d,
                    "magnitude"     :m,
                    "magnitude type":mt,
                    "region"        :a,
                    }
                
                self.__map_df = pd.DataFrame.from_dict(event_dict)
                self.__table_model = TableModel(self.__map_df)
                self.table_events.setModel(self.__table_model)
                self.table_events.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
                self.table_events.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

            # plotting events as magnitude vs. time
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
                self.worker.progress.emit("error during the process, check internet connection!")
        # print(self.data["events"])

    def _on_btn_selectevent_tbl_clicked(self):
        """
        """
        ind = [idx.row() for idx in self.table_events.selectionModel().selectedRows()]
        if ind != []:
            ind = ind[0]
            self.data["selected event"] = self.data["events"][ind]
            self._printLn2(self.data["selected event"].__str__())
            self.show_events_in_mpl_2_ind(ind)

    def _on_btn_show_events_clicked(self):
        """
        considering searching and loading events in a thread
        """
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

        # show event button is disabled during process
        self.btn_showevents.setEnabled(False)
        self.thread.finished.connect(
            lambda: self.btn_showevents.setEnabled(True)
        )
        self.thread.finished.connect(lambda: self.btn_rectangle.setChecked(False))
        
    def _on_btn_show_stations_clicked(self):
        """
        """
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
        """
        """
        otime = self.data["selected event"].origins[0].time
        t1 = otime + self.configs["waveform time"][0]
        t2 = otime + self.configs["waveform time"][1]
        # t1 = ob.UTCDateTime(self.datetime_start.dateTime().toPyDateTime())
        # t2 = ob.UTCDateTime(self.datetime_end.dateTime().toPyDateTime())
        (minlon, maxlon), (minlat, maxlat) = self.mpl_select_map_2.mpl.data

        if self.worker != None:
            self.worker.progress.emit("\nsearch stations . . .")

        try:
            client = RoutingClient("iris-federator")
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
        
        except Exception as error:
            if self.worker != None:
                self.worker.progress.emit(str(type(error).__name__) + "–" + str(error))
                self.worker.progress.emit("error during the process, check internet connection!")

    def _on_btn_show_stations_circ_clicked(self):
        """
        """
        self.thread = QtCore.QThread()
        self.worker = Worker(self._show_stations_circ)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(lambda: self._printLn("finished!"))
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.progress[str].connect(self._printLn)
        self.thread.start()

        # Final resets
        self.btn_showstations_circ.setEnabled(False)
        self.thread.finished.connect(
            lambda: self.btn_showstations_circ.setEnabled(True)
        )

    def _show_stations_circ(self):
        """
        """

        otime = self.data["selected event"].origins[0].time
        t1 = otime + self.configs["waveform time"][0]
        t2 = otime + self.configs["waveform time"][1]
        evlon = self.data["selected event"].origins[0].longitude
        evlat = self.data["selected event"].origins[0].latitude

        if self.worker != None:
            self.worker.progress.emit("\nsearch stations . . .")

        try:
            minr = float(self.txt_circle_min.text())
            maxr = float(self.txt_circle_max.text())
            client = RoutingClient("iris-federator")
            self.data["stations"] = client.get_stations(network=self.configs["network filter"], channel=self.configs["channel filter"], starttime=t1,
                                        endtime=t2,level="response",
                                        latitude=evlat, longitude=evlon, minradius=minr, maxradius=maxr)
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

            self.mpl_select_map_2.mpl.draw()
        
        except Exception as error:
            if self.worker != None:
                self.worker.progress.emit(str(type(error).__name__) + "–" + str(error))
                self.worker.progress.emit("error during the process, check internet connection!")
    
    def _load_station_in_map(self):
        """
        """
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Station File", "", "XML Files (*.STATIONXML *.xml)")
        if fileName:
            try:
                self._printLn("read data " + fileName) 
                self.data["stations"] = ob.read_inventory(fileName)
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
                self._printLn("data being plotted . . .")

                self.mpl_select_map_2.mpl.draw()
                self._printLn("finished!")
            except:
                self._printLn("error!")
    
    def show_events_in_mpl_2(self, mpl):
        """
        """
        idx = mpl.ind
        self.show_events_in_mpl_2_ind(idx)
        

    def show_events_in_mpl_2_ind(self, idx):
        self.mpl_select_map_2.mpl.axes.cla()
        self.draw_basemap(self.mpl_select_map_2.mpl)
        self.mpl_select_map_2.mpl._activate_rectangle()
        # gdf_map = gpd.read_file('./coastlines/ne_110m_land.shp')
        ax = self.mpl_select_map_2.mpl.axes
        # gdf_map.plot(ax=ax, clip_on=False)        
        ax.plot(self.data["events"][idx].origins[0].longitude,
                self.data["events"][idx].origins[0].latitude,
                'ro', clip_on=False)
        self.mpl_select_map_2.mpl.draw()

    def _select_stations(self, bool):
        """
        """
        try:
            if self.stat_txts != []:
                for txt in self.stat_txts:
                    txt.remove()
                self.mpl_select_map_2.mpl.draw()
                self.stat_txts = []

            if self._circ is not None:
                self._circ.remove()
                self._circ = None

            if bool == True:
                ax = self.mpl_select_map_2.mpl.axes
                self.stat_selector = SelectFromCollection(ax, self.stat_points)
                self.stat_selector.communicate.sigEmpty.connect(self.__select_stations_by_indices)

            else:
                self.stat_selector.disconnect()
                self.mpl_select_map_2.mpl.draw()
        except:
            MBoxLbl("Error selecting stations!", self)

    def _on_btn_selectstations_circle_clicked(self):
        try:
            if self.stat_txts != []:
                for txt in self.stat_txts:
                    txt.remove()
                self.mpl_select_map_2.mpl.draw()
                self.stat_txts = []
            
            if self._circ is not None:
                self._circ.remove()
                self._circ = None

            ax = self.mpl_select_map_2.mpl.axes
            canvas = ax.figure.canvas
            
            evlon = self.data["selected event"].origins[0].longitude
            evlat = self.data["selected event"].origins[0].latitude
            self._circ = Circle((evlon, evlat), radius = float(self.txt_circle.text()))

            xys = self.stat_points.get_offsets()
            Npts = len(xys)

            fc = self.stat_points.get_facecolors()
            if len(fc) == 1:
                fc = np.tile(fc, (Npts, 1))
            ind = np.nonzero(self._circ.contains_points(xys))[0]
            fc[:, -1] = 0.3
            fc[ind, -1] = 1
            self.stat_points.set_facecolors(fc)

            self._circ.set_facecolor('none')
            self._circ.set_edgecolor('red')
            ax.add_artist(self._circ)
            canvas.draw()

            self.__select_stations_by_indices_base(ind)

        except:
            MBoxLbl("Error selecting stations!", self)

    def __select_stations_by_indices(self):
        """
        """
        self.__select_stations_by_indices_base(self.stat_selector.ind)

    def __select_stations_by_indices_base(self, ind):
        """
        """
        self.data["selected stations"] = None
        for __n, idx in enumerate(ind):
            i, j = self.__pass_inv[f"{idx}"]
            inv_i = self.data["stations"][i][j]
            net = self.data["stations"][i]._code
            st = inv_i._code
            if __n == 0:
                self.data["selected stations"] = self.data["stations"].select(network=net, station=st)
            else:
                self.data["selected stations"].extend(self.data["stations"].select(network=net, station=st))

    def _on_btn_get_waveforms_clicked(self):
        """
        """
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
        """
        """
        g = Geod(ellps=self.configs["geod reference"])

        otime = self.data["selected event"].origins[0].time
        t1 = otime + self.configs["waveform time"][0]
        t2 = otime + self.configs["waveform time"][1]

        evlon = self.data["selected event"].origins[0].longitude
        evlat = self.data["selected event"].origins[0].latitude

        try:
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

        except:
            if self.worker != None:
                self.worker.progress.emit("error during the process, check internet connection!")            

    def _show_waveforms(self):
        """
        """
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
        """
        """
        flt = ["STATIONXML Files (*.STATIONXML)",
               "SEISAN HYP Files (*.hyp)",
                  "STATIONTXT Files (*.STATIONTXT)",
                  "SACPZ Files (*.SACPZ)",
                  "KML Files (*.KML)"]
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Stations", "", ";;".join(flt))
        if fileName:
            try:
                ext = os.path.splitext(fileName)[1].replace(".","").upper()
                if self.data["selected stations"] is not None:
                    if ext == "HYP":
                        self._save_seisan_hyp(fileName)
                        self._printLn2(f"saving station data to {fileName}")
                    else:
                        self.data["selected stations"].write(fileName, format=ext)
                        self._printLn2(f"saving station data to {fileName}")
            except:
                pass

    def _save_seisan_hyp(self, filename):
        inv = self.data["selected stations"]
        with open(filename, 'w') as f:
            stat_lis = []
            for netObj in inv:
                for stObj in netObj:
                    for chObj in stObj:
                        sta = stObj._code
                        if sta not in stat_lis:
                            stat_lis.append(sta)
                            if len(sta) > 5: continue
                            str_sta = f"  {sta:4}" if (len(sta) <= 4) else f" {sta:5}"
                            lat = chObj._latitude
                            slat = "N" if (np.sign(lat) >= 0) else "S"
                            lat = np.abs(lat)
                            dlat = int(lat)
                            mlat = 60 * (lat - dlat)
                            lon = chObj._longitude
                            slon = "E" if (np.sign(lon) >= 0) else "W"
                            lon = np.abs(lon)
                            dlon = int(lon)
                            mlon = 60 * (lon - dlon)
                            elev = chObj._elevation
                            elev = int(elev)
                            s_hyp = f"{str_sta}{dlat:2d}{mlat:5.2f}{slat:1}{dlon:3d}{mlon:5.2f}{slon:1}{elev:4d}\n"
                            f.write(s_hyp)
    
    def _save_waveforms(self):
        """
        """
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Waveforms", "", 
                                                            "MSEED Files (*.mseed);;SAC Files (*.sac)")
        if fileName:
            if self.data["waveforms"] != None:
                ext = os.path.splitext(fileName)[1]
                st = self.data["waveforms"].copy()
                if self.chk_merge_traces.isChecked():
                    st.merge(method=1, interpolation_samples=-1, fill_value='interpolate')
                st.write(fileName, format=ext.replace(".","").upper())
                self._printLn2(f"saving waveform data to {fileName}")

    def _on_btn_save_events_clicked(self):
        """
        """
        flt = ["ASCII Files (*.CSV)",
                  "QUAKEML Files (*.QUAKEML)",
                  "ZMAP Files (*.ZMAP)",
                  "NORDIC Files (*.NORDIC)",
                  "HYPODDPHA Files (*.HYPODDPHA)",
                  "KML Files (*.KML)",
                  "JSON Files (*.JSON)"]
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Events", "",
                                                            ";;".join(flt))
        if fileName:
            try:
                ext = os.path.splitext(fileName)[1].replace(".","").upper()
                if ext == 'CSV':
                    self.__map_df.to_csv(fileName, index=False)
                else:
                    self.data["events"].write(fileName, format=ext)
            except:
                pass

    def _on_btn_load_events_clicked(self):
        flt = ["*.QUAKEML",
               "*.NORDIC"]
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Event File", "", f"Event File ({' '.join(flt)})")
        if fileName:
            try:
                ext = os.path.splitext(fileName)[1].replace(".","").upper()
                self.data["events"] = ob.read_events(fileName, format=ext)

                x = []
                y = []
                m = []
                mt = []
                d = []
                t = []
                tutc = []
                a = []
                for event in self.data["events"]:
                    x.append(event.origins[0].longitude)
                    y.append(event.origins[0].latitude)
                    m.append(event.magnitudes[0].mag)
                    mt.append(event.magnitudes[0].magnitude_type)
                    t.append(event.origins[0].time.matplotlib_date)
                    d.append(event.origins[0].depth/1000)
                    tutc.append(str(event.origins[0].time))
                    a.append(event.event_descriptions[0].text)
                
                self._printLn("plotting . . .")

                # plotting events to the basemap
                ax = self.mpl_select_map.mpl.axes
                ax.plot(x, y, 'ro', picker=10, clip_on=False)
                self.mpl_select_map.mpl.draw()

                # creating a table
                if self.chk_showtable.isChecked():
                    if self.worker != None:
                        self.worker.progress.emit("creating a table . . .")
                    event_dict = {
                        "origin time"   :tutc,
                        "longitude"     :x, 
                        "latitude"      :y, 
                        "depth"         :d,
                        "magnitude"     :m,
                        "magnitude type":mt,
                        "region"        :a,
                        }
                    
                    self.__map_df = pd.DataFrame.from_dict(event_dict)
                    self.__table_model = TableModel(self.__map_df)
                    self.table_events.setModel(self.__table_model)
                    self.table_events.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
                    self.table_events.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

                # plotting events as magnitude vs. time
                self.mpl_select_map_plot.mpl.axes.cla()
                ax = self.mpl_select_map_plot.mpl.axes
                ax.plot(t, m, 'ro', picker=10, clip_on=False)
                ax.xaxis_date()
                ax.figure.autofmt_xdate()
                ax.set_ylabel("Magnitude")
                ax.set_xlabel("Time")
                self.mpl_select_map_plot.mpl.draw()
                self._printLn("finished!")
            except:
                self._printLn("Error reading the event file!")

    def _show_waveforms_in_new_window(self):
        if self.data['waveforms'] is not None:
            st = self.data['waveforms']
            fig = plt.figure()
            st.plot(fig=fig)
            plt.show()

def main():
    app = QtWidgets.QApplication(sys.argv)
    main = SearchByMaps()
    main.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()