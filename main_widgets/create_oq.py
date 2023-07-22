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
                ["File path", "savepath", None, None, ("Save Catalogue", "", "ASCII Files (*.csv)")],
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
        self.__MTfile = None
        self.__FMDfile = None
        self.__MCfile = None
        self.__ABfile = None

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
        if self.tree_list["Declustering"][0][3].currentIndex() == 1:
            inputfile = self.tree_list['Catalogue'][0][3].text.toPlainText()
            outputfile = self.tree_list['Declustering'][1][3].text.toPlainText()
            self.declustering(inputfile, outputfile)
        inputfile = None
        if self.tree_list["Declustering"][0][3].currentIndex() == 0:
            inputfile = self.tree_list['Catalogue'][0][3].text.toPlainText()
        else:
            inputfile = self.tree_list['Declustering'][1][3].text.toPlainText()
        
        if self.tree_list["Mc"][0][3].currentIndex() == 1:
            out, self.__MCfile = self.apply_func(MC, inputfile)
            self._printLn(out)

        if self.tree_list["a-b value"][0][3].currentIndex() == 1:
            out, self.__ABfile = self.apply_func(ABvalue, [inputfile, self.__MCfile])
            self._printLn(out)

        if self.tree_list["Map"][0][3].currentIndex() == 1:
            if self.chk_map_overwrite.isChecked(): self.mpl_map_reset(self.map_view.mpl)
            df = pd.read_csv(inputfile)
            ax = self.map_view.mpl.figure.axes[0]
            marker = self.tree_list['Map'][1][3].toPlainText()
            size = int(self.tree_list['Map'][2][3].toPlainText())
            color = self.tree_list['Map'][3][3].toPlainText()
            ax.scatter(df["longitude"], df["latitude"], c=color, marker=marker, s=size)
            self.map_view.mpl.draw()
        
        if self.tree_list["Plot"][0][3].currentIndex() == 1:
            out, self.__MTfile = self.apply_func(MTdensity, inputfile)
            self._printLn(out)

        if self.tree_list["Plot"][1][3].currentIndex() == 1:
            if self.tree_list["a-b value"][0][3].currentIndex() == 0:
                out, self.__FMDfile = self.apply_func(FMD, inputfile)
                self._printLn(out)
            else:
                out, self.__FMDfile = self.apply_func(FMD_AB, [inputfile, self.__ABfile])
                self._printLn(out)            

    def __plot_show(self):
        chk = 0
        if self.tree_list["Plot"][0][3].currentIndex() == 1:
            if self.tree_list["Mc"][0][3].currentIndex() == 0:
                plot_MTdensity([self.__MTfile])
            else:
                plot_MTdensity([self.__MTfile, self.__MCfile])
            chk = 1
        
        if self.tree_list["Plot"][1][3].currentIndex() == 1:
            if self.tree_list["a-b value"][0][3].currentIndex() == 0:
                plot_FMD(self.__FMDfile)
            else:
                plot_FMD_AB(self.__FMDfile)
            chk = 1
        
        if chk:
            plt.show()
            
    def _on_btn_python_path_clicked(self):
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Python in OQ", "", "")
        if fileName:
            try:
                self.txt_python_path.setText(fileName)
            except: pass