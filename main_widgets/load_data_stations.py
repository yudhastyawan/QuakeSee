from PyQt5 import QtWidgets, uic, QtCore
import obspy as ob
import geopandas as gpd
import os
from libs.commons import Worker
from libs.utils import TableModel
from widgets.mplcanvas import MplCanvasBaseWithToolbarTab
from obspy.clients.fdsn.header import URL_MAPPINGS
from obspy.clients.fdsn.client import Client
from pyproj import Geod
from matplotlib.transforms import blended_transform_factory
import pandas as pd
import numpy as np
import matplotlib as mplib
from obspy.core.inventory.response import paz_to_sacpz_string

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
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Station File", "", "XML Files (*.STATIONXML *.xml)")
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
                # self.table_stations.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
                # self.table_stations.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)

            except: pass
    
    def contextMenuEvent(self, event):
        self.menu = QtWidgets.QMenu(self.table_stations)
        self.plot_menu_disp = self.menu.addAction("Plot Response (DISP)")
        self.plot_menu_disp.triggered.connect(self.__on_plot_menu_disp_clicked)
        self.plot_menu_vel = self.menu.addAction("Plot Response (VEL)")
        self.plot_menu_vel.triggered.connect(self.__on_plot_menu_clicked)
        self.plot_menu_acc = self.menu.addAction("Plot Response (ACC)")
        self.plot_menu_acc.triggered.connect(self.__on_plot_menu_acc_clicked)
        self.plot_menu_loc = self.menu.addAction("Plot Location")
        self.plot_menu_loc.triggered.connect(self.__on_plot_menu_loc_clicked)
        self.menu.exec_(event.globalPos())

    def __on_plot_menu_clicked(self):
        idcs = [idx.row() for idx in self.table_stations.selectionModel().selectedRows()]
        self._resp_wid = MplCanvasBaseWithToolbarTab(N=len(idcs))
        for i, idx in enumerate(idcs):
            ax = self._resp_wid.canvas[i].mpl.axes
            fig = ax.figure
            fig.clf()
            axes = [fig.add_axes([0.1, 0.5, 0.7, 0.4]), fig.add_axes([0.1, 0.1, 0.7, 0.4])]
            n, s, l, c = self.__station_df.loc[idx, ["network", "station", "location", "channel"]]
            self.__inv.plot_response(0.001, output='VEL', network=n, station=s, 
                                     location=l, channel=c, show=False, axes=axes)
        self._resp_wid.show()

        # idcs = [idx.row() for idx in self.table_stations.selectionModel().selectedRows()]
        # for idx in idcs:
        #     n, s, l, c = self.__station_df.loc[idx, ["network", "station", "location", "channel"]]
        #     self.__inv.plot_response(0.001, output='VEL', network=n, station=s, location=l, channel=c)

        # self.__st = ob.Stream([self.data["waveforms"].traces[i] for i in self.__plot_rows])
        # self.__show_waveplots(self.tab_waveplots.widgetCanvas.mpl, self.__st)
        # self.__update_mpl_to_tight(self.tab_waveplots.widgetCanvas.mpl)

    def __on_plot_menu_disp_clicked(self):
        idcs = [idx.row() for idx in self.table_stations.selectionModel().selectedRows()]
        self._resp_wid = MplCanvasBaseWithToolbarTab(N=len(idcs))
        for i, idx in enumerate(idcs):
            ax = self._resp_wid.canvas[i].mpl.axes
            fig = ax.figure
            fig.clf()
            axes = [fig.add_axes([0.1, 0.5, 0.7, 0.4]), fig.add_axes([0.1, 0.1, 0.7, 0.4])]
            n, s, l, c = self.__station_df.loc[idx, ["network", "station", "location", "channel"]]
            self.__inv.plot_response(0.001, output='DISP', network=n, station=s, 
                                     location=l, channel=c, show=False, axes=axes)
        self._resp_wid.show()

    def __on_plot_menu_acc_clicked(self):
        idcs = [idx.row() for idx in self.table_stations.selectionModel().selectedRows()]
        self._resp_wid = MplCanvasBaseWithToolbarTab(N=len(idcs))
        for i, idx in enumerate(idcs):
            ax = self._resp_wid.canvas[i].mpl.axes
            fig = ax.figure
            fig.clf()
            axes = [fig.add_axes([0.1, 0.5, 0.7, 0.4]), fig.add_axes([0.1, 0.1, 0.7, 0.4])]
            n, s, l, c = self.__station_df.loc[idx, ["network", "station", "location", "channel"]]
            self.__inv.plot_response(0.001, output='ACC', network=n, station=s, 
                                     location=l, channel=c, show=False, axes=axes)
        self._resp_wid.show()

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

    def _on_btn_save_stations_clicked(self):
        flt = ["SEISAN HYP Files (*.hyp)",
                  "STATIONXML Files (*.STATIONXML)",
                  "STATIONTXT Files (*.STATIONTXT)",
                  "SACPZ Files (*.SACPZ)",
                  "KML Files (*.KML)"]
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save station", "", 
                                                            ";;".join(flt))
        if fileName:
            ext = os.path.splitext(fileName)[1].replace(".","").upper()
            if ext == "HYP":
                if self.__station_df is not None:
                    self._save_seisan_hyp(fileName)
                    self._printLn2(f"saving station data to {fileName}")
            else:
                if self.__inv is not None:
                    self.__inv.write(fileName, format=ext)
                    self._printLn2(f"saving station data to {fileName}")

    def _save_seisan_hyp(self, filename):
        df = self.__station_df
        with open(filename, 'w') as f:
            stat_lis = []
            for _, d in df.iterrows():
                sta = d.station
                if sta not in stat_lis:
                    stat_lis.append(sta)
                    if len(sta) > 5: continue
                    str_sta = f"  {sta:4}" if (len(sta) <= 4) else f" {sta:5}"
                    lat = d.latitude
                    slat = "N" if (np.sign(lat) >= 0) else "S"
                    lat = np.abs(lat)
                    dlat = int(lat)
                    mlat = 60 * (lat - dlat)
                    lon = d.longitude
                    slon = "E" if (np.sign(lon) >= 0) else "W"
                    lon = np.abs(lon)
                    dlon = int(lon)
                    mlon = 60 * (lon - dlon)
                    elev = d.elevation
                    elev = int(elev)
                    s_hyp = f"{str_sta}{dlat:2d}{mlat:5.2f}{slat:1}{dlon:3d}{mlon:5.2f}{slon:1}{elev:4d}\n"
                    f.write(s_hyp)

    def _save_seisan_sacpz(self):
        dir_name = QtWidgets.QFileDialog.getExistingDirectory(self, "Select a Directory")
        if dir_name:
            if self.__inv is not None:
                for netObj in self.__inv:
                    for stObj in netObj:
                        for chObj in stObj:
                            resp = chObj.response
                            sens = resp.instrument_sensitivity
                            try:
                                paz = resp.get_paz()
                            except:
                                continue
                            input_unit = sens.input_units.upper()
                            if input_unit == "M":
                                pass
                            elif input_unit in ["M/S", "M/SEC"]:
                                paz.zeros.append(0j)
                            elif input_unit in ["M/S**2", "M/SEC**2"]:
                                paz.zeros.extend([0j, 0j])
                            else:
                                continue
                            sacpz = paz_to_sacpz_string(paz, sens)
                            sta = f"{stObj._code:5}".replace(" ", "_")
                            chan = chObj._code[0] + "__" + chObj._code[-1]
                            stdate = stObj.start_date.strftime("%Y-%m-%d-%H%M")
                            # sacpz = chObj.response.get_sacpz()
                            fname = sta + chan + "." + stdate + "_SAC"
                            with open(os.path.join(dir_name, fname), "w") as f:
                                f.write(sacpz)
                self._printLn("sacpz files has been saved in " + dir_name)