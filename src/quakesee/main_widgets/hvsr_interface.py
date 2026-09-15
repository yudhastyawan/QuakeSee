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


class HVSRInterface(QtWidgets.QWidget):
    def __init__(self, parent = None):
        QtWidgets.QWidget.__init__(self, parent)

        #Load the UI Page
        uic.loadUi('./ui/hvsr.ui', self)

        kernel_dict = {
            "_hvsr":self,
        }

        self._push_kernel = lambda: self.py_console.push_kernel(kernel_dict)

        self._print = lambda x: self.py_console._append_plain_text(x, True)
        self._printLn = lambda x: self._print(x + "\n")
        self._printLn2 = lambda x: self._print("\n" + x + "\n")

        self._forward_models = None

    def _on_btn_layers_clicked(self):
        nlayers = self.txt_layers.text()
        if nlayers:
            nlayers = int(nlayers)
            self._forward_models = np.zeros((nlayers,6))
            self._forward_models[:,0] = 5.
            self._forward_models[-1,0] = np.inf
            self._forward_models[:,1] = 200.
            self._forward_models[:,2] = hvratio.Vs2Vp(self._forward_models[:,1])
            self._forward_models[:,3] = hvratio.Vp2Density(self._forward_models[:,2])
            self._forward_models[:,4:6] = 30

            self.table_layers.setRowCount(nlayers)

            self.__set_table_layers()

    def __set_table_layers(self):
        for r in range(self.table_layers.rowCount()):
            for c in range(self.table_layers.columnCount()):
                x = f"{self._forward_models[r,c]:.2f}"
                self.table_layers.setItem(r, c, QtWidgets.QTableWidgetItem(x))
    
    def _on_btn_reset_layers_clicked(self):
        self.table_layers.setRowCount(0)

    def _table_layers_onCellChanged(self, row, column):
        text = self.table_layers.item(row, column).text()
        number = float(text)
        self._forward_models[row, column] = number

    def _on_btn_vpe_clicked(self):
        self._forward_models[:,2] = hvratio.Vs2Vp(self._forward_models[:,1])
        self.__set_table_layers()

    def _on_btn_rhoe_clicked(self):
        self._forward_models[:,3] = hvratio.Vp2Density(self._forward_models[:,2])
        self.__set_table_layers()

    def _on_btn_forward_apply_clicked(self):
        k_Q = float(self.txt_k_Q.text())
        Fref = float(self.txt_freq_ref.text())
        H = self._forward_models[0:-1,0]
        vs = self._forward_models[:,1]
        vp = self._forward_models[:,2]
        density = self._forward_models[:,3]
        Qs = self._forward_models[:,4]
        Qp = self._forward_models[:,5]
        Fmin = float(self.txt_freq_min.text())
        Fmax = float(self.txt_freq_max.text())
        FN = int(self.txt_freq_n.text())
        if self.combo_freq.currentIndex() == 0:
            F = np.linspace(Fmin,Fmax,FN)
        else:
            F = np.logspace(np.log10(Fmin),np.log10(Fmax),FN)
        AMPp = hvratio.AMP(vp, density, H, Qp, k_Q, Fref, F)
        AMPs = hvratio.AMP(vs, density, H, Qs, k_Q, Fref, F)
        HV = AMPs/AMPp

        mpl = self.canvas_forward.mpl

        if self.combo_view.currentIndex() == 0: mpl.axes.cla()
        mpl.axes.plot(F, AMPp, color='grey', linestyle="--", linewidth=1, label="$AMP_P$")
        mpl.axes.plot(F, AMPs, color='black', linestyle="--", linewidth=1, label="$AMP_S$")
        mpl.axes.plot(F, HV, color=self.wid_color.color.getRgbF()[0:3], linestyle="-", linewidth=2, label="$HVSR$")

        mpl.axes.semilogx()
        mpl.axes.set_xlabel("Frequency (Hz)")
        mpl.axes.set_ylabel("Amplitude")
        mpl.axes.legend()

        mpl.draw()