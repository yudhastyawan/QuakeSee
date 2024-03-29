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


class RaspShake(QtWidgets.QWidget):
    def __init__(self, parent = None):
        QtWidgets.QWidget.__init__(self, parent)

        #Load the UI Page
        uic.loadUi('./ui/raspshake.ui', self)

        kernel_dict = {
            "_rasp":self,
        }

        self._push_kernel = lambda: self.py_console.push_kernel(kernel_dict)

        self._print = lambda x: self.py_console._append_plain_text(x, True)
        self._printLn = lambda x: self._print(x + "\n")
        self._printLn2 = lambda x: self._print("\n" + x + "\n")

        self.datetime_start.setDateTime(QtCore.QDateTime.currentDateTime().addSecs(- 42 * 60))
        self.datetime_end.setDateTime(QtCore.QDateTime.currentDateTime().addSecs(- 2 * 60))

    def _on_btn_set_datetime_clicked(self):
        date_now = datetime.utcnow().strftime("%d %b %Y %H:%M:%S")
        command = "sudo -k date --set \"" + date_now + "\""

        # Update the next three lines with your
        # server's information

        host = self.txt_host.text()
        username = self.txt_user.text()
        password = self.txt_pass.text()

        try:
            client = paramiko.client.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(host, username=username, password=password)
            _stdin, _stdout, _stderr = client.exec_command(command)
            _stdin.write(password + '\n')
            _stdin.flush()
            self._printLn(str(_stdout.read().decode()))
            self._printLn(str(_stderr.read().decode()))
            _stdin.close()
            client.close()
            MBoxLbl("DateTime has been set!", self)
        except:
            MBoxLbl("Error during the process, check connection to Raspberry Shake!", self)

    def _on_btn_wave_check_clicked(self):
        try:
            client = Client(self.txt_wave_host.text(), int(self.txt_wave_port.text()))
            response = client.get_availability(self.txt_wave_net.text(), self.txt_wave_stat.text(), channel=self.txt_wave_chan.text()[0:2] + 'Z')
            self._printLn(str(response))
        except:
            MBoxLbl("Error during the process, check connection to Raspberry Shake / input parameters!", self)

    def _on_btn_wave_plot_clicked(self):
        t1 = ob.UTCDateTime(self.datetime_start.dateTime().toPyDateTime()) - (3600 * 7)
        t2 = ob.UTCDateTime(self.datetime_end.dateTime().toPyDateTime()) - (3600 * 7)

        try:
            client = Client(self.txt_wave_host.text(), int(self.txt_wave_port.text()))

            st = client.get_waveforms(self.txt_wave_net.text(), 
                                    self.txt_wave_stat.text(), 
                                    self.txt_wave_loc.text(), 
                                    self.txt_wave_chan.text(), t1, t2)
            self._printLn(str(st))
            fig = plt.figure()
            st.plot(fig=fig)
            plt.show()
            # plt.close(fig)

        except:
            MBoxLbl("Error during the process, check connection to Raspberry Shake / input parameters!", self)            

    def _on_btn_wave_save_clicked(self):
        t1 = ob.UTCDateTime(self.datetime_start.dateTime().toPyDateTime()) - (3600 * 7)
        t2 = ob.UTCDateTime(self.datetime_end.dateTime().toPyDateTime()) - (3600 * 7)

        try:
            client = Client(self.txt_wave_host.text(), int(self.txt_wave_port.text()))

            st = client.get_waveforms(self.txt_wave_net.text(), 
                                    self.txt_wave_stat.text(), 
                                    self.txt_wave_loc.text(), 
                                    self.txt_wave_chan.text(), t1, t2)
            self._printLn(str(st))

            fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Waveforms", "", "MSEED Files (*.mseed)")
            if fileName:
                try:
                    st.write(fileName, "MSEED")
                except:
                    pass

        except:
            MBoxLbl("Error during the process, check connection to Raspberry Shake / input parameters!", self)

    def _on_btn_wave_start_clicked(self):
        try:
            client = eClient(self.txt_real_host.text(), int(self.txt_real_port.text()))
            self.worker = Worker(client, 
                                self.txt_real_net.text(), 
                                self.txt_real_stat.text(), 
                                self.txt_real_loc.text(), 
                                self.txt_real_chan.text(), 
                                delay_time = int(self.txt_real_up_time.text()), 
                                st_time = int(self.txt_real_st_time.text()))
            self.thread = QtCore.QThread()
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

    def __init__(self, client, net, stat, loc, chan, delay_time = 1, st_time = 5):
        super().__init__()
        self.client = client
        self.delay_time = delay_time
        self.st_time = st_time
        self.net = net
        self.stat = stat
        self.loc = loc
        self.chan = chan

    def run(self):
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.delay_time * 1000)
        self.timer.timeout.connect(self.get_st)

    def start(self):
        self.timer.start()

    def stop(self):
        self.timer.stop()

    def get_st(self):
        t2 = ob.UTCDateTime.now() - 10
        t1 = t2 - self.st_time
        st = self.client.get_waveforms(self.net, self.stat, self.loc, self.chan, t1, t2)

        self.signal_data.emit(st)