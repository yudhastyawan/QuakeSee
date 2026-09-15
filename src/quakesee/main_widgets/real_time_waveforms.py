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
import matplotlib.pyplot as plt


class RealTimeWaveforms(QtWidgets.QWidget):
    def __init__(self, parent = None):
        QtWidgets.QWidget.__init__(self, parent)

        #Load the UI Page
        uic.loadUi('./ui/real_time_waveforms.ui', self)

        kernel_dict = {
            "_realtime":self,
        }

        self._push_kernel = lambda: self.py_console.push_kernel(kernel_dict)

        self._print = lambda x: self.py_console._append_plain_text(x, True)
        self._printLn = lambda x: self._print(x + "\n")
        self._printLn2 = lambda x: self._print("\n" + x + "\n")

        self.thread = None

    def _on_btn_wave_kill_clicked(self):
        if self.thread is not None:
            self.thread.quit()
            self.thread.wait()

    def _on_btn_wave_start_clicked(self):
        try:
            if self.thread is not None:
                self.thread.quit()
                self.thread.wait()
            client = Client(self.txt_real_host.text())
            self.worker = Worker(client, 
                                self.txt_real_net.text(), 
                                self.txt_real_stat.text(), 
                                self.txt_real_loc.text(), 
                                self.txt_real_chan.text(), 
                                delay_time = int(self.txt_real_up_time.text()), 
                                st_time = int(self.txt_real_st_time.text()),
                                hour_now = int(self.txt_real_hour_now.text()))
            self.thread = QtCore.QThread(parent=self)
            self.worker.moveToThread(self.thread)
            self.worker.signal_data.connect(self.update_plot)
            self.btn_wave_resume.clicked.connect(self.worker.start)
            self.btn_wave_stop.clicked.connect(self.worker.stop)
            self.thread.started.connect(self.worker.run)
            self.thread.start()
        except:
            MBoxLbl("Error during the process, check connection to Raspberry Shake / input parameters!", self)
        

    def update_plot(self, st):
        mpl = self.wave_live.mpl
        mpl.axes.get_figure().clf()

        st.plot(fig = mpl.axes.get_figure())
        # self.canvas.axes.get_figure().get_axes()[0].set_ylim([-7300, -6900])
        mpl.draw()

class Worker(QtCore.QObject):
    signal_data = QtCore.pyqtSignal(ob.Stream)
    signal_stop = QtCore.pyqtSignal()
    signal_start = QtCore.pyqtSignal()

    def __init__(self, client, net, stat, loc, chan, delay_time = 1, st_time = 5, hour_now = 7):
        super().__init__()
        self.client = client
        self.delay_time = delay_time
        self.st_time = st_time
        self.net = net
        self.stat = stat
        self.loc = loc
        self.chan = chan
        self.hour_now = hour_now

    def run(self):
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.delay_time * 1000)
        self.timer.timeout.connect(self.get_st)
        self.timer.start()

    def start(self):
        self.timer.start()

    def stop(self):
        self.timer.stop()

    def get_st(self):
        t2 = ob.UTCDateTime.now() - 3600 * self.hour_now
        t1 = t2 - self.st_time
        st = self.client.get_waveforms(self.net, self.stat, self.loc, self.chan, t1, t2)

        self.signal_data.emit(st)