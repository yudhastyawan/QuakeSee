from PyQt5 import QtWidgets, QtCore
from widgets.mplcanvas import MplCanvasBase
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT

class PlotWaveforms(QtWidgets.QWidget):
    def __init__(self, parent = None):
        QtWidgets.QWidget.__init__(self, parent)

        vlay = QtWidgets.QVBoxLayout()
        vlay.setContentsMargins(0,0,0,0)
        vlay.setSpacing(0)
        self.scroll_area = QtWidgets.QScrollArea()
        self.widgetCanvas = WidgetMplCanvas()
        fig = self.widgetCanvas.mpl.axes.figure
        fig.clf()
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.widgetCanvas)
        self.toolbar = NavigationToolbar2QT(self.widgetCanvas.mpl, self)
        vlay.addWidget(self.toolbar)
        vlay.addWidget(self.scroll_area)
        self.setLayout(vlay)

class WidgetMplCanvas(QtWidgets.QWidget):
    def __init__(self, parent = None):
        QtWidgets.QWidget.__init__(self, parent)
        # self.setMinimumHeight(2000)
        vlay = QtWidgets.QVBoxLayout()
        vlay.setContentsMargins(0,0,0,0)
        vlay.setSpacing(0)
        self.mpl = MplCanvasBase()
        vlay.addWidget(self.mpl)
        self.setLayout(vlay)