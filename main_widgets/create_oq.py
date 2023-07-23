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
import matplotlib as mplib
from libs.embed_openquake import *
import pickle
import matplotlib.pyplot as plt
import geopandas as gpd
import glob
from libs.utils import TableModel
import random
from matplotlib.lines import Line2D

import matplotlib
matplotlib.rcParams['mathtext.fontset'] = 'custom'
matplotlib.rcParams['mathtext.rm'] = 'Times New Roman'
matplotlib.rcParams['mathtext.it'] = 'Times New Roman:italic'
matplotlib.rcParams['mathtext.bf'] = 'Times New Roman:bold'

class CreateOQ(QtWidgets.QWidget):
    def __init__(self, parent = None):
        QtWidgets.QWidget.__init__(self, parent)

        #Load the UI Page
        uic.loadUi('./ui/create_oq.ui', self)

        self.tree_list = {
            "Catalogue": [
                ["File path", "path", None, None, ("Open Catalogue", "", "ASCII Files (*.csv)")],
            ],
            "Declustering": [
                ["apply", "bool", None, None],
            ],
            "Mc": [
                ["apply", "bool", None, None],
                ["Mc", "option", None, None, ['Stepp1971', 'Max. Curvature']],
            ],
            "a-b value": [
                ["apply", "bool", None, None],
            ],
            "Map": [
                ["Seismicity", "bool", None, None],
                ["marker", "number", None, None],
                ["size", "number", None, None],
                ["color", "number", None, None],
            ],
            "Plot": [
                ["M - T Density", "bool", None, None],
                ["FMD", "bool", None, None],
                ["Autosave (X)", "bool", None, None],
            ],
        }

        self.tree_oq.tree_list = self.tree_list
        self.tree_list = self.tree_oq.input_to_tree_model()

        self._print = lambda x: self.py_console._append_plain_text(x, True)
        self._printLn = lambda x: self._print(x + "\n")
        self._printLn2 = lambda x: self._print("\n" + x + "\n")

        self.txt_python_path.setText("/Users/yudhastyawan/openquake/bin/python")
        self.tree_list['Map'][1][3].setText("o")
        self.tree_list['Map'][2][3].setText("5")
        self.tree_list['Map'][3][3].setText("red")

        self.__gdf_area = None
        self.__dict_area_depth = {"upper depth": [], "lower depth": []}

        self.mpl_map_reset(self.map_view.mpl)

    def mpl_map_reset(self, mpl):
        """
        reset the map to a blank canvas
        """        
        mpl.axes.cla()
        self.draw_basemap(mpl)


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

    def __pybin(self):
        return self.txt_python_path.toPlainText()

    def declustering(self, inputfile, outputfile):
        output = declustering(self.__pybin(), inputfile, outputfile)
        self._printLn(str(output))

    def plot_func(self, func, inputfile):
        output = func(self.__pybin(), inputfile)
        self._printLn(str(output))
    
    def apply_func(self, func, inputfile):
        output = func(self.__pybin(), inputfile)
        return output

    def _on_btn_apply_clicked(self):
        self.prog_apply.setValue(50)
        self.thread = QtCore.QThread()
        self.worker = Worker(self.__apply_thread)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

        self.worker.finished.connect(lambda: self.__plot_show())
        self.worker.finished.connect(lambda: self.__delete_pkl())
        self.worker.finished.connect(lambda: self.prog_apply.setValue(100))

    def __delete_pkl(self):
        dirp = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tmp")
        if os.path.isdir(dirp):
            for fname in glob.glob(os.path.join(dirp, "*")):
                os.remove(fname)

    def __apply_thread(self):

        inputfile = self.tree_list['Catalogue'][0][3].text.toPlainText()
        if inputfile == "": return

        for fn in inputfile.split('\n'):
            if self.tree_list["Declustering"][0][3].currentIndex() == 1:
                ofile = os.path.join(self.txt_outdir.text(), os.path.splitext(os.path.split(fn)[-1])[0] + "_declustered.csv")
                self.declustering(fn, ofile)
                if os.path.isfile(fn): fn = ofile        
        
            if self.tree_list["Mc"][0][3].currentIndex() == 1:
                out, _ = self.apply_func(MC, fn)
                self._printLn(out)

            if self.tree_list["a-b value"][0][3].currentIndex() == 1:
                out, _ = self.apply_func(ABvalue, fn)
                self._printLn(out)

            if self.tree_list["Map"][0][3].currentIndex() == 1:
                if self.chk_map_overwrite.isChecked(): self.mpl_map_reset(self.map_view.mpl)
                df = pd.read_csv(fn)
                ax = self.map_view.mpl.figure.axes[0]
                marker = self.tree_list['Map'][1][3].toPlainText()
                size = int(self.tree_list['Map'][2][3].toPlainText())
                color = self.tree_list['Map'][3][3].toPlainText()
                ax.scatter(df["longitude"], df["latitude"], c=color, marker=marker, s=size)
                self.map_view.mpl.draw()
            
            if self.tree_list["Plot"][0][3].currentIndex() == 1:
                out, _ = self.apply_func(MTdensity, fn)
                self._printLn(out)

            if self.tree_list["Plot"][1][3].currentIndex() == 1:
                if self.tree_list["a-b value"][0][3].currentIndex() == 0:
                    out, _ = self.apply_func(FMD, fn)
                    self._printLn(out)
                else:
                    out, _ = self.apply_func(FMD_AB, fn)
                    self._printLn(out)

    def __plot_show(self):
        chk = 0
        
        inputfile = self.tree_list['Catalogue'][0][3].text.toPlainText()
        if inputfile == "": return

        for fn in inputfile.split('\n'):
            if self.tree_list["Declustering"][0][3].currentIndex() == 1:
                ofile = os.path.join(self.txt_outdir.text(), os.path.splitext(os.path.split(fn)[-1])[0] + "_declustered.csv")
                if os.path.isfile(fn): fn = ofile

            if self.tree_list["Plot"][0][3].currentIndex() == 1:
                plot_MTdensity(fn)
                chk = 1
        
            if self.tree_list["Plot"][1][3].currentIndex() == 1:
                if self.tree_list["a-b value"][0][3].currentIndex() == 0:
                    plot_FMD(fn)
                else:
                    plot_FMD_AB(fn)
                chk = 1
        
        if chk:
            plt.show()
            
    def _on_btn_python_path_clicked(self):
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Python in OQ", "", "")
        if fileName:
            try:
                self.txt_python_path.setText(fileName)
            except: pass

    def _on_btn_load_shp_clicked(self):
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Shape File", "", "SHP File (*.shp)")
        if fileName:
            try:
                gdf = gpd.read_file(fileName)
                gdf["filename"] = os.path.split(fileName)[-1]
                if self.chk_area_shp_overwrite.isChecked():
                    self.__gdf_area = gdf
                else:
                    self.__gdf_area = gpd.GeoDataFrame(pd.concat([self.__gdf_area, gdf], ignore_index=True))
                gdf = self.__gdf_area.drop(columns='geometry')
                gdf['geometry'] = [geom.geom_type for geom in self.__gdf_area.geometry]
                table_model = TableModel(gdf)
                self.table_area.setModel(table_model)
                self.table_area.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
                self.table_area.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
            except: pass

    def _on_btn_area_dep2tbl_clicked(self):
        self.__dict_area_depth["upper depth"].append(float(self.txt_area_Z1.text()))
        self.__dict_area_depth["lower depth"].append(float(self.txt_area_Z2.text()))
        df = pd.DataFrame.from_dict(self.__dict_area_depth)
        table_model = TableModel(df)
        self.table_area_depth.setModel(table_model)
        self.table_area_depth.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_area_depth.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

    def _on_btn_area_cut_clicked(self):
        self.prog_apply.setValue(50)
        self.thread = QtCore.QThread()
        self.worker = Worker(self.__area_cut)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

        self.worker.finished.connect(lambda: self.__delete_pkl())
        self.worker.finished.connect(lambda: self.prog_apply.setValue(100))

    def __area_cut(self):
        inputfile = self.tree_list['Catalogue'][0][3].text.toPlainText()
        outputdir = self.txt_outdir.text()
        geom_rows = [idx.row() for idx in self.table_area.selectionModel().selectedRows()]
        area_geoms = [
            geom.exterior.xy for geom in self.__gdf_area.iloc[geom_rows].geometry
        ]
        if geom_rows:
            for fn in inputfile.split('\n'):
                area_cut(self.__pybin(), fn, outputdir, area_geoms, self.__dict_area_depth)

    def _on_btn_outdir_clicked(self):
        dir_name = QtWidgets.QFileDialog.getExistingDirectory(self, "Select a Directory")
        if dir_name:
            self.txt_outdir.setText(dir_name)

    def _on_btn_area_depth_clear_clicked(self):
        self.__dict_area_depth = {"upper depth": [], "lower depth": []}
        df = pd.DataFrame.from_dict(self.__dict_area_depth)
        table_model = TableModel(df)
        self.table_area_depth.setModel(table_model)
        self.table_area_depth.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_area_depth.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

    def _on_btn_area_load_preview_clicked(self):
        ax = self.area_preview.mpl.figure.axes[0]
        ax.cla()
        geom_rows = [idx.row() for idx in self.table_area.selectionModel().selectedRows()]
        get_colors = lambda n: ["#%06x" % random.randint(0, 0xFFFFFF) for _ in range(n)]
        if geom_rows:
            clrs = get_colors(len(geom_rows))
            self.__gdf_area.iloc[geom_rows].plot(color='none', edgecolor=clrs, 
                                                 linewidth=1, ax=ax)
            lines = [Line2D([0], [0], linestyle="none", marker="s", markersize=10, 
               markeredgecolor=clr, markerfacecolor='none') for clr in clrs]
            ax.legend(lines, geom_rows)
        self.area_preview.mpl.draw()