import sys
import matplotlib
matplotlib.use('Qt5Agg')

from PyQt5 import QtCore, QtWidgets

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
import matplotlib.widgets as mwidgets
import numpy as np

from libs.utils import Communicate

class MplCanvasBase(FigureCanvasQTAgg):

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvasBase, self).__init__(fig)

class MplCanvasMap(MplCanvasBase):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi, layout="constrained")
        self.axes = fig.add_subplot(111)
        super(MplCanvasMap, self).__init__(fig)

        self.data_base = [[-180, 180], [-90, 90]]
        self.data = [[-180, 180], [-90, 90]]

        self.event_handler = None
        self.communicate = Communicate()

        self._activate_rectangle()

    def _activate_rectangle(self):
        self.rect = mwidgets.RectangleSelector(self.axes, self._line_select_callback,
                       useblit=False, button=[1], 
                       minspanx=5, minspany=5, spancoords='pixels', 
                       interactive=True)
        self.rect.set_active(False)

    def _line_select_callback(self, eclick, erelease):
        x1, y1 = eclick.xdata, eclick.ydata
        x2, y2 = erelease.xdata, erelease.ydata
        self.data = [[x1, x2], [y1, y2]]

    def select_rectangle(self, bool):
        self.rect.set_active(bool)
        if bool == False:
            self.rect.set_visible(False)
            self.rect.update()
            self.data = self.data_base

    def _on_pick(self, event):
        artist = event.artist
        # xmouse, ymouse = event.mouseevent.xdata, event.mouseevent.ydata
        # x, y = artist.get_xdata(), artist.get_ydata()
        ind = event.ind
        self.ind = int(ind[0])
        self.communicate.sig.emit(self.ind)

        # print('Artist picked:', event.artist)
        # print('{} vertices picked'.format(len(ind)))
        # print('Pick between vertices {} and {}'.format(min(ind), max(ind)+1))
        # print('x, y of mouse: {:.2f},{:.2f}'.format(xmouse, ymouse))
        # print('Data point:', x[ind[0]], y[ind[0]])

    def select_event(self, bool):
        if bool == True:
            self.event_handler = self.callbacks.connect('pick_event', self._on_pick)
        else:
            if self.event_handler != None:
                self.callbacks.disconnect(self.event_handler)

class MplCanvasMapWithToolbar(QtWidgets.QWidget):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        self.vlayout = QtWidgets.QVBoxLayout()
        self.mpl = MplCanvasMap()
        self.toolbar = NavigationToolbar2QT(self.mpl, self)
        self.vlayout.addWidget(self.toolbar)
        self.vlayout.addWidget(self.mpl)
        self.setLayout(self.vlayout)
    
    def select_rectangle(self, bool):
        self.mpl.select_rectangle(bool)
    
    def select_event(self, bool):
        self.mpl.select_event(bool)

class MplCanvasBaseWithToolbar(QtWidgets.QWidget):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        self.vlayout = QtWidgets.QVBoxLayout()
        self.mpl = MplCanvasBase()
        self.toolbar = NavigationToolbar2QT(self.mpl, self)
        self.vlayout.addWidget(self.toolbar)
        self.vlayout.addWidget(self.mpl)
        self.setLayout(self.vlayout)