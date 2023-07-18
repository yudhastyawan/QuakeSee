from PyQt5 import QtWidgets, uic, QtCore
import obspy as ob
import geopandas as gpd
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
import matplotlib as mplib

class LoadDataStations(QtWidgets.QWidget):
    def __init__(self, parent = None):
        QtWidgets.QWidget.__init__(self, parent)

        #Load the UI Page
        uic.loadUi('./ui/load_data_stations.ui', self)

        # variables
        self.__inv = None
        self.__station_df = None

        kernel_dict = {
            "_st":self,
        }

        self._push_kernel = lambda: self.py_console.push_kernel(kernel_dict)

        self._print = lambda x: self.py_console._append_plain_text(x, True)
        self._printLn = lambda x: self._print(x + "\n")
        self._printLn2 = lambda x: self._print("\n" + x + "\n")

    def _on_btn_load_stations_clicked(self):
        """
        """
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Station File", "", "XML Files (*.xml)")
        if fileName:
            try: 
                self.__inv = ob.read_inventory(fileName)

                st_dict = {"network":[], "station":[], "location":[], "channel":[], 
                           "latitude":[], "longitude":[], "elevation":[], "depth":[],
                           "sampling rate":[], "azimuth":[], "dip":[]}
                for netObj in self.__inv:
                    for stObj in netObj:
                        for chObj in stObj:
                            st_dict["network"].append(netObj._code)
                            st_dict["station"].append(stObj._code)
                            st_dict["channel"].append(chObj._code)
                            st_dict["location"].append(chObj._location_code)
                            st_dict["latitude"].append(chObj._latitude)
                            st_dict["longitude"].append(chObj._longitude)
                            st_dict["elevation"].append(chObj._elevation)
                            st_dict["depth"].append(chObj._depth)
                            st_dict["azimuth"].append(chObj._azimuth)
                            st_dict["dip"].append(chObj._dip)
                            st_dict["sampling rate"].append(chObj._sample_rate)
                
                self.__station_df = pd.DataFrame.from_dict(st_dict)
                self.__table_station_model = TableModel(self.__station_df)
                self.table_stations.setModel(self.__table_station_model)
                self.table_stations.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
                self.table_stations.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)

            except: pass
    
    def contextMenuEvent(self, event):
        self.menu = QtWidgets.QMenu(self.table_stations)
        self.plot_menu = self.menu.addAction("Plot Response")
        self.plot_menu.triggered.connect(self.__on_plot_menu_clicked)
        self.plot_menu_loc = self.menu.addAction("Plot Location")
        self.plot_menu_loc.triggered.connect(self.__on_plot_menu_loc_clicked)
        self.menu.exec_(event.globalPos())

    def __on_plot_menu_clicked(self):
        idcs = [idx.row() for idx in self.table_stations.selectionModel().selectedRows()]
        for idx in idcs:
            n, s, l, c = self.__station_df.loc[idx, ["network", "station", "location", "channel"]]
            self.__inv.plot_response(0.001, network=n, station=s, location=l, channel=c)

        # self.__st = ob.Stream([self.data["waveforms"].traces[i] for i in self.__plot_rows])
        # self.__show_waveplots(self.tab_waveplots.widgetCanvas.mpl, self.__st)
        # self.__update_mpl_to_tight(self.tab_waveplots.widgetCanvas.mpl)

    def __on_plot_menu_loc_clicked(self):
        idcs = [idx.row() for idx in self.table_stations.selectionModel().selectedRows()]
        x, y, txt = [], [], []
        for idx in idcs:
            xx, yy = self.__station_df.loc[idx, ["longitude", "latitude"]]
            tt = ".".join(self.__station_df.loc[idx, ["network", "station", "location", "channel"]])
            x.append(xx)
            y.append(yy)
            txt.append(tt)
        
        mpl = self.canvas_station.mpl
        mpl.axes.cla()
        self.draw_basemap(mpl)
        mpl.axes.scatter(x, y, c='k', s=80, marker='^', clip_on=False)

        for i, j, k in zip(x, y, txt):
            mpl.axes.text(i, j, k, clip_on=False)

        mpl.draw()

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