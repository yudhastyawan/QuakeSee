from PyQt5 import QtWidgets, uic, QtCore
import obspy as ob
import geopandas as gpd
import os
from libs.commons import Worker
from libs.utils import TableModel
from widgets.messagebox import MBox, MBoxLbl
from widgets.mplcanvas import MplCanvasBaseWithToolbar
from obspy.clients.fdsn.header import URL_MAPPINGS
from obspy.clients.fdsn.client import Client
from pyproj import Geod
from matplotlib.transforms import blended_transform_factory
import pandas as pd
import numpy as np
import matplotlib as mplib
import paramiko
from datetime import datetime
from obspy.clients.earthworm import Client as eClient
import matplotlib.pyplot as plt
import libs.hvratio as hvratio
from matplotlib.patches import Polygon
import requests
import time
import io
from sympy.parsing.sympy_parser import parse_expr
from sympy.utilities.lambdify import lambdify
import sympy as sp


class DownloadISC(QtWidgets.QWidget):
    def __init__(self, parent = None):
        QtWidgets.QWidget.__init__(self, parent)

        #Load the UI Page
        uic.loadUi('./ui/download_isc.ui', self)

        kernel_dict = {
            "_isc":self,
        }

        self._push_kernel = lambda: self.py_console.push_kernel(kernel_dict)

        self._print = lambda x: self.py_console._append_plain_text(x, True)
        self._printLn = lambda x: self._print(x + "\n")
        self._printLn2 = lambda x: self._print("\n" + x + "\n")

        self._forward_models = None
        self._data = []
        self._poly = None
        self._points = None
        self._saved_data = None
        self.__fileNames = None

        self._func_list = [
            ["0.7212 * M + 1.4433", "mb, Mb, mB, MB", "0", "3.7"],
            ["1.0107 * M + 0.0801", "mb, Mb, mB, MB", "3.7", "8.3"],
            ["0.6016 * M + 2.476", "ms, Ms, mS, MS", "2.8", "6.2"],
            ["0.9239 * M + 0.5671", "ms, Ms, mS, MS", "6.2", "8.7"],
            ["1 * M", "ml, Ml, mL, ML, mlv, MLv, MLV, mLv, mLV", "0", "10"],
            ["1 * M", "mw, Mw, mW, MW, mww, Mww, Mwc, MWw, MWc", "0", "10"],
        ]

        self._func_list_to_table()

        self.draw_basemap(self.canvas_map.mpl)
        cid = self.canvas_map.mpl.mpl_connect('button_press_event', self.mpl_onclick)

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

    def mpl_onclick(self, event):
        mpl = self.canvas_map.mpl
        ax = mpl.axes
        if event.button == 1:
            self._data.append([event.xdata, event.ydata])
            dat = np.array(self._data)
            if self._points is not None: 
                self._points.remove()
                mpl.draw()
            self._points, = ax.plot(dat[:,0], dat[:,1], 'ro-')
            mpl.draw()
            self._printLn('lon=%f, lat=%f' % (event.xdata, event.ydata))
            
        elif event.button == 3:
            if self._poly is not None: 
                self._poly.remove()
                mpl.draw()

            self._poly = Polygon(self._data, facecolor = 'red', alpha=0.5)
            ax.add_patch(self._poly)
            mpl.draw()
            self._saved_data = self._data
            self._data = []
            geoms = ",".join([",".join(list(map(str,r))[::-1]) for r in self._saved_data])

            self.txt_coords.setText(geoms)

    def _on_btn_dir_clicked(self):
        dir_name = QtWidgets.QFileDialog.getExistingDirectory(self, "Select a Directory")
        if dir_name:
            self.txt_dir.setText(dir_name)

    def _on_btn_apply_clicked(self):
        self.thread = QtCore.QThread()
        self.worker = Worker(self.__download)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.progress.connect(self._printLn)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

        self.worker.finished.connect(lambda: self._printLn("Finished!"))

    def __download(self):
        out_format=self.txt_outfmt.text()
        request=self.txt_request.text()
        searchshape=self.txt_shape.text()
        coordvals=self.txt_coords.text()
        min_dep=self.txt_min_dep.text()
        max_dep=self.txt_max_dep.text()
        null_dep=self.txt_null_dep.text()
        min_mag=self.txt_min_mag.text()
        max_mag=self.txt_max_mag.text()
        null_mag=self.txt_null_mag.text()
        req_mag_type=self.txt_mag_type.text()
        req_mag_agcy=self.txt_mag_ag.text()
        min_year = int(self.txt_min_year.text())
        max_year = int(self.txt_max_year.text())
        n_years = int(self.txt_n_years.text())

        list_year = list(range(min_year, max_year, n_years))
        if list_year[-1] != max_year:
            list_year += [max_year]
        for first_year, last_year in zip(list_year[0:-1], list_year[1::]):
            self.worker.progress.emit(str((first_year, last_year)))
            start_year=first_year
            start_month=1
            start_day=1
            start_time='00%3A00%3A00'
            end_year=last_year
            end_month=12
            end_day=31
            end_time='23%3A59%3A59'
            url = "http://isc.ac.uk/cgi-bin/web-db-run?" + \
                    f"out_format={out_format}" + \
                    f"&request={request}" + \
                    f"&searchshape={searchshape}" + \
                    f"&coordvals={coordvals}" + \
                    f"&start_year={start_year}" + \
                    f"&start_month={start_month}" + \
                    f"&start_day={start_day}" + \
                    f"&start_time={start_time}" + \
                    f"&end_year={end_year}" + \
                    f"&end_month={end_month}" + \
                    f"&end_day={end_day}" + \
                    f"&end_time={end_time}" + \
                    f"&min_dep={min_dep}" + \
                    f"&max_dep={max_dep}" + \
                    f"&null_dep={null_dep}" + \
                    f"&min_mag={min_mag}" + \
                    f"&max_mag={max_mag}" + \
                    f"&null_mag={null_mag}" + \
                    f"&req_mag_type={req_mag_type}" + \
                    f"&req_mag_agcy={req_mag_agcy}"

            self.worker.progress.emit(url)
            r = requests.get(url, allow_redirects=True)
            text = r.text
            idx = text.find("----EVENT-----")
            if idx != -1:
                time.sleep(5)
                with open(os.path.join(self.txt_dir.text(), f'ISC_{start_year}-{start_month}-{start_day}_{end_year}-{end_month}-{end_day}.txt'), 'w') as f:
                    f.write(text)

    def _func_list_to_table(self):
        nRows = len(self._func_list)
        self.table_func.setRowCount(nRows)
        for r in range(self.table_func.rowCount()):
            for c in range(self.table_func.columnCount()):
                x = self._func_list[r][c]
                self.table_func.setItem(r, c, QtWidgets.QTableWidgetItem(x))

        header = self.table_func.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)

    def _table_func_onCellChanged(self, row, column):
        text = self.table_func.item(row, column).text()
        if text == '': text = None
        self._func_list[row][column] = text

    def _on_btn_load_catalogues_clicked(self):
        fileNames, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Open Catalogue", "", "ASCII Files (*.txt)")
        self.__fileNames = fileNames
        if fileNames:
            self.list_catalogues.clear()
            self.list_catalogues.addItems(fileNames)

    def _on_btn_convert_clicked(self):
        self.thread = QtCore.QThread()
        self.worker = Worker(self.__convert)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.progress.connect(self._printLn)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

        self.worker.finished.connect(lambda: self._printLn("Finished!"))

    def __convert(self):
        fileNames = self.__fileNames
        if fileNames is not None:
            func_list = self._func_list

            fn = []
            selected_func = []
            for i, (f, opt, _, _) in enumerate(func_list):
                if (f is not None) and (opt is not None):
                    x = sp.Symbol('x')
                    fs = parse_expr(f, transformations='all', local_dict={'M': x})
                    opt = opt.replace(' ','')
                    fn.append([lambdify(x, fs, 'numpy'), opt.split(',')])
                    selected_func.append(func_list[i])

            def avg_Mw(d):
                m_arr = []

                for i in range(0,len(d),3):
                    for (f, opt), (_, _, lim1, lim2) in zip(fn, selected_func):
                        mi = float(d[i+2])
                        if lim1 is None: lim1 = -np.inf
                        if lim2 is None: lim2 = np.inf
                        if d[i+1] in opt and (mi >= float(lim1) and mi < float(lim2)):
                            m_arr.append(f(mi))

                if len(m_arr) > 0:
                    return [1, np.average(m_arr), np.std(m_arr)]
                else:
                    return [0, 0., 0.]

            all_outlists = []
            first_name = ""
            for fi, fname in enumerate(fileNames):
                self.worker.progress.emit("converting " + os.path.split(fname)[-1])
                with open(fname, "r") as f:
                    text = f.read()
                    idx = text.find("----EVENT-----")
                    idx = text[idx::].find("\n") + idx
                    id_stop = text.find("STOP")
                    data_string = text[idx:id_stop].replace(" ", "")
                    data_split = data_string.split('\n')[2::]
                    data_split.remove('')
                    data_string = [",".join(d.split(',')[0:9]) for d in data_split]
                    data_mag = [d.split(',')[9::] for d in data_split]
                    data_mag = [[x for x in d if x != ''] for d in data_mag]
                    data_idcs = [j for j,d in enumerate(data_mag) if d != []]
                    data_string = [data_string[j] for j in data_idcs]
                    data_mag = [d for d in data_mag if d != []]

                if data_string == []: continue

                data_string = "\n".join(data_string)

                names = ["EVENTID","TYPE","AUTHOR","DATE","TIME","LAT","LON","DEPTH","DEPFIX"]

                df = pd.read_csv(io.StringIO(data_string), sep=',', names=names)
                df["MAG"] = data_mag

                Mw_list = np.array([avg_Mw(d) for d in data_mag])

                df["Mw"] = Mw_list[:,1]
                df["s_Mw"] = Mw_list[:,2]

                Mw_chk = np.where(Mw_list[:,0] == 1)[0]

                mainlist = df.iloc[Mw_chk].apply(lambda x: str(x['EVENTID']) + "," + x['DATE'].split('-')[0] + "," + \
                                                            x['DATE'].split('-')[1] + "," + \
                                                            x['DATE'].split('-')[2] + "," + \
                                                            x['TIME'].split(':')[0] + "," + \
                                                            x['TIME'].split(':')[1] + "," + \
                                                            x['TIME'].split(':')[2] + "," + \
                                                            str(x['LON']) + "," + \
                                                            str(x['LAT']) + "," + \
                                                            str(x['DEPTH']) + "," + \
                                                            f"{x['Mw']:.2f}" + "," + f"{x['s_Mw']:.2f}", axis=1).to_list()
                
                outlist = ["eventID,year,month,day,hour,minute,second,longitude,latitude,depth,magnitude,sigmaMagnitude"]
                outlist += mainlist

                
                all_outlists += mainlist
                first_name = fname
                with open(os.path.splitext(fname)[0] + "_OQ.csv", "w") as f:
                    f.write("\n".join(outlist))

            if all_outlists != []:
                all_outlists.insert(0, "eventID,year,month,day,hour,minute,second,longitude,latitude,depth,magnitude,sigmaMagnitude")
                with open(os.path.join(os.path.split(first_name)[0],"all_OQ.csv"), "w") as f:
                    f.write("\n".join(all_outlists))

    def _on_btn_add_table_func_clicked(self):
        self.table_func.setRowCount(self.table_func.rowCount() + 1)
        l = [None] * 4
        self._func_list.append(l)

    def _on_btn_sub_table_func_clicked(self):
        self.table_func.setRowCount(self.table_func.rowCount() - 1)
        self._func_list.pop(-1)