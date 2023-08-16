from PyQt5 import QtWidgets, uic, QtCore
import obspy as ob
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
from libs.embed_openquake import *
import pickle
import matplotlib.pyplot as plt
import geopandas as gpd
import glob
from libs.utils import TableModel
import random
from matplotlib.lines import Line2D
from pyproj import Transformer
from shapely import LineString
import yaml

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
            "Filter (X)": [
                ["apply", "bool", None, None],
                ["upper depth", "number", None, None],
                ["lower depth", "number", None, None],
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
                ["Autosave", "bool", None, None],
            ],
        }

        kernel_dict = {
            "_oq":self,
        }

        self._push_kernel = lambda: self.py_console.push_kernel(kernel_dict)

        self.tree_oq.tree_list = self.tree_list
        self.tree_list = self.tree_oq.input_to_tree_model()

        self._print = lambda x: self.py_console._append_plain_text(x, True)
        self._printLn = lambda x: self._print(x + "\n")
        self._printLn2 = lambda x: self._print("\n" + x + "\n")

        self.__userconfigs = None

        parentdir = os.path.dirname(os.path.dirname(__file__))
        userfile = os.path.join(parentdir, "user.yaml")
        if os.path.isfile(userfile):
            with open(userfile, 'r') as f:
                self.__userconfigs = yaml.safe_load(f)

        if self.__userconfigs != None:
            self.txt_python_path.setText(self.__userconfigs["path_OQ"]["python"])
            self.txt_outdir.setText(self.__userconfigs["path_OQ"]["outputdir"])
            
        self.tree_list['Map'][1][3].setText("o")
        self.tree_list['Map'][2][3].setText("5")
        self.tree_list['Map'][3][3].setText("red")

        self.__gdf_area = None
        self.__gdf_fault = None
        self.__fault_props = None
        self.__dict_area_depth = {"upper depth": [], "lower depth": []}
        self._chk_shell = 0

        self.mpl_map_reset(self.map_view.mpl)

        # check_shell
        # if self.txt_python_path.text() != "": 
        #     self._chk_shell = self.check_shell()
        #     if self._chk_shell == 0: MBox("Check Python Path!", "Make sure the OpenQuake Python is exist.", self)

        # if self.txt_outdir.text() != "":
        #     if not os.path.isdir(self.txt_outdir.text()): 
        #         MBoxLbl("Make sure the output directory is exist!", self)

        self.txt_python_path.textChanged[str].connect(self.__check_chk_shell)

    def _chk_on_program_load(self):
        # check_shell
        if self.txt_python_path.text() != "": 
            self._chk_shell = self.check_shell()
            if self._chk_shell == 0: print("ERROR!\nCheck Python Path!\nMake sure the OpenQuake Python in Create OQ Input is exist!")

        if self.txt_outdir.text() != "":
            if not os.path.isdir(self.txt_outdir.text()): 
                print("ERROR!\nCheck the Output Directory!\nMake sure the output directory of Create OQ Inputs is exist!")

    def __check_chk_shell(self, txt):
        if os.path.isfile(txt):
            self._chk_shell = check_shell(txt)
            if self._chk_shell == 0:
                MBoxLbl("Make sure the Python path is exist", self)
        else:
            MBoxLbl("The Python path is not exist", self)

    def check_shell(self):
        if os.path.isfile(self.__pybin()):
            return check_shell(self.__pybin())
        else:
            return 0

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
        return self.txt_python_path.text()

    def declustering(self, inputfile, outputfile, chk=1):
        output = declustering(self.__pybin(), inputfile, outputfile, chk=chk)
        self._printLn(str(output))

    def plot_func(self, func, inputfile):
        output = func(self.__pybin(), inputfile)
        self._printLn(str(output))
    
    def apply_func(self, func, inputfile, chk=1):
        output = func(self.__pybin(), inputfile, chk=chk)
        return output

    def _on_btn_apply_clicked(self):
        outdir = self.txt_outdir.text()
        if not os.path.isdir(outdir): 
            MBoxLbl("Make sure the output directory is exist!", self)
            return
        
        if self._chk_shell == 0: 
            MBox("Check Python Path!", "Make sure the OpenQuake Python is exist.", self)
            return

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
        chk = self._chk_shell
        outdir = self.txt_outdir.text()

        inputfile = self.tree_list['Catalogue'][0][3].text.toPlainText()
        if inputfile == "": return

        for fn in inputfile.split('\n'):
            if self.tree_list["Declustering"][0][3].currentIndex() == 1:
                ofile = os.path.join(outdir, os.path.splitext(os.path.split(fn)[-1])[0] + "_declustered.csv")
                self.declustering(fn, ofile, chk=chk)
                if os.path.isfile(fn): fn = ofile        
        
            if self.tree_list["Mc"][0][3].currentIndex() == 1:
                out, _ = self.apply_func(MC, fn, chk=chk)
                self._printLn(out)

            if self.tree_list["a-b value"][0][3].currentIndex() == 1:
                out, _ = self.apply_func(ABvalue, fn, chk=chk)
                self._printLn(out)
            
            if self.tree_list["Plot"][0][3].currentIndex() == 1:
                out, _ = self.apply_func(MTdensity, fn, chk=chk)
                self._printLn(out)

            if self.tree_list["Plot"][1][3].currentIndex() == 1:
                if self.tree_list["a-b value"][0][3].currentIndex() == 0:
                    out, _ = self.apply_func(FMD, fn, chk=chk)
                    self._printLn(out)
                else:
                    out, _ = self.apply_func(FMD_AB, fn, chk=chk)
                    self._printLn(out)

    def __plot_show(self):
        chk = 0
        issave = self.tree_list["Plot"][2][3].currentIndex()
        outputdir = self.txt_outdir.text()
        
        inputfile = self.tree_list['Catalogue'][0][3].text.toPlainText()
        if inputfile == "": return

        for fn in inputfile.split('\n'):
            if self.tree_list["Declustering"][0][3].currentIndex() == 1:
                ofile = os.path.join(self.txt_outdir.text(), os.path.splitext(os.path.split(fn)[-1])[0] + "_declustered.csv")
                if os.path.isfile(fn): fn = ofile

            if self.tree_list["Map"][0][3].currentIndex() == 1:
                if self.chk_map_overwrite.isChecked(): self.mpl_map_reset(self.map_view.mpl)
                df = pd.read_csv(fn)
                ax = self.map_view.mpl.figure.axes[0]
                marker = self.tree_list['Map'][1][3].text()
                size = int(self.tree_list['Map'][2][3].text())
                color = self.tree_list['Map'][3][3].text()
                ax.scatter(df["longitude"], df["latitude"], c=color, marker=marker, s=size)
                self.map_view.mpl.draw()

            if self.tree_list["Plot"][0][3].currentIndex() == 1:
                plot_MTdensity(fn, outputdir, issave)
                chk = 1
        
            if self.tree_list["Plot"][1][3].currentIndex() == 1:
                if self.tree_list["a-b value"][0][3].currentIndex() == 0:
                    plot_FMD(fn, outputdir, issave)
                else:
                    plot_FMD_AB(fn, outputdir, issave)
                chk = 1
        
        if chk and (issave == 0):
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
            except: MBoxLbl("Error Loading *.shp file!", self)
    
    def _on_btn_fault_shp_clicked(self):
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Shape File", "", "SHP File (*.shp)")
        if fileName:
            try:
                gdf = gpd.read_file(fileName)
                gdf["filename"] = os.path.split(fileName)[-1]
                if self.chk_fault_shp_overwrite.isChecked():
                    self.__gdf_fault = gdf
                else:
                    self.__gdf_fault = gpd.GeoDataFrame(pd.concat([self.__gdf_fault, gdf], ignore_index=True))
                gdf = self.__gdf_fault.drop(columns='geometry')
                gdf['geometry'] = [geom.geom_type for geom in self.__gdf_fault.geometry]
                table_model = TableModel(gdf)
                self.table_fault.setModel(table_model)
                self.table_fault.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
                self.table_fault.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)

                nRows = len(self.__gdf_fault.index)
                if self.chk_fault_shp_overwrite.isChecked():
                    self.__fault_props = np.zeros((nRows, self.table_fault_props.columnCount()))
                    self.__fault_props[:,1] = 20
                    self.__fault_props[:,2] = 90
                    self.__fault_props[:,3] = 20
                
                self.table_fault_props.setRowCount(nRows)
                for r in range(self.table_fault_props.rowCount()):
                    for c in range(self.table_fault_props.columnCount()):
                        x = str(self.__fault_props[r,c])
                        self.table_fault_props.setItem(r, c, QtWidgets.QTableWidgetItem(x))

                self.table_fault_props.setVerticalHeaderLabels([str(s) for s in range(nRows)])
            except: MBoxLbl("Error Loading *.shp file!", self)

    def _table_fault_props_onCellChanged(self, row, column):
        text = self.table_fault_props.item(row, column).text()
        number = float(text)
        self.__fault_props[row, column] = number

    def _on_btn_area_dep2tbl_clicked(self):
        self.__dict_area_depth["upper depth"].append(float(self.txt_area_Z1.text()))
        self.__dict_area_depth["lower depth"].append(float(self.txt_area_Z2.text()))
        df = pd.DataFrame.from_dict(self.__dict_area_depth)
        table_model = TableModel(df)
        self.table_area_depth.setModel(table_model)
        self.table_area_depth.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_area_depth.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

    def _on_btn_area_cut_clicked(self):
        outdir = self.txt_outdir.text()
        if not os.path.isdir(outdir): 
            MBoxLbl("Make sure the output directory is exist!", self)
            return
        
        if self._chk_shell == 0: 
            MBox("Check Python Path!", "Make sure the OpenQuake Python is exist.", self)
            return
        
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
        chk = self._chk_shell
        inputfile = self.tree_list['Catalogue'][0][3].text.toPlainText()
        outputdir = self.txt_outdir.text()
        geom_rows = [idx.row() for idx in self.table_area.selectionModel().selectedRows()]
        area_geoms = [
            geom.exterior.xy for geom in self.__gdf_area.iloc[geom_rows].geometry
        ]
        if geom_rows:
            for fn in inputfile.split('\n'):
                area_cut(self.__pybin(), fn, outputdir, area_geoms, self.__dict_area_depth, chk=chk)

    def _on_btn_fault_cut_clicked(self):
        outdir = self.txt_outdir.text()
        if not os.path.isdir(outdir): 
            MBoxLbl("Make sure the output directory is exist!", self)
            return
        
        if self._chk_shell == 0: 
            MBox("Check Python Path!", "Make sure the OpenQuake Python is exist.", self)
            return
        
        self.prog_apply.setValue(50)
        self.thread = QtCore.QThread()
        self.worker = Worker(self.__fault_cut)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

        self.worker.finished.connect(lambda: self.__delete_pkl())
        if self.chk_fault_view_3D.isChecked(): self.worker.finished.connect(lambda: self.__view_3D_after_fault_cut())
        self.worker.finished.connect(lambda: self.prog_apply.setValue(100))

    def __fault_cut(self):
        chk = self._chk_shell
        inputfile = self.tree_list['Catalogue'][0][3].text.toPlainText()
        outputdir = self.txt_outdir.text()

        if (inputfile == '') or (outputdir == ''): return

        geom_rows = [idx.row() for idx in self.table_fault.selectionModel().selectedRows()]
        
        if geom_rows:
            fault_geoms = [
                geom.xy for geom in self.__gdf_fault.iloc[geom_rows].geometry
            ]
            fault_props = self.__fault_props[geom_rows, :]

            for fn in inputfile.split('\n'):
                fault_cut(self.__pybin(), fn, outputdir, fault_geoms, fault_props, chk=chk)

    def __view_3D_after_fault_cut(self, localcoords=False):
        outdir = self.txt_outdir.text()
        if not os.path.isdir(outdir): 
            MBoxLbl("Make sure the output directory is exist!", self)
            return
        
        if self._chk_shell == 0: 
            MBox("Check Python Path!", "Make sure the OpenQuake Python is exist.", self)
            return
        
        self.prog_apply.setValue(50)
        self.thread = QtCore.QThread()
        self.worker = Worker(self.__fault_mesh)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

        self.worker.finished.connect(lambda: self.__after_view_3D_after_fault_cut(localcoords))
        self.worker.finished.connect(lambda: self.prog_apply.setValue(100))

    def __fault_mesh(self):
        inputfile = 'temp'
        chk = self._chk_shell

        geom_rows = [idx.row() for idx in self.table_fault.selectionModel().selectedRows()]
        
        if geom_rows:
            fault_geoms = [
                geom.xy for geom in self.__gdf_fault.iloc[geom_rows].geometry
            ]
            fault_props = self.__fault_props[geom_rows, :]

            fault_mesh(self.__pybin(), inputfile, fault_geoms, fault_props, chk=chk)

    def __after_view_3D_after_fault_cut(self, localcoords=False):
        inputfile = self.tree_list['Catalogue'][0][3].text.toPlainText()
        outputdir = self.txt_outdir.text()

        geom_rows = [idx.row() for idx in self.table_fault.selectionModel().selectedRows()]
        get_colors = lambda n: ["#%06x" % random.randint(0, 0xFFFFFF) for _ in range(len(n))]

        if geom_rows:
            fault_geoms = [
                geom.xy for geom in self.__gdf_fault.iloc[geom_rows].geometry
            ]

            clrs = get_colors(fault_geoms)

            ax = self.fault_preview_3D.mpl.figure.axes[0]
            ax.cla()

            outputfile = embed_pn("temp", "fault_mesh.pkl")
            with open(outputfile, 'rb') as f:
                mesh = pickle.load(f)

            for i, (geom, clr) in enumerate(zip(fault_geoms, clrs)):
                x, y = geom
                if localcoords:
                    x, y = self.LL2localcoords(x, y)
                ax.plot(x, y, np.zeros(len(x)), color=clr)

                fx, fy, fz = mesh[i][0], mesh[i][1], mesh[i][2]
                if localcoords:
                    fx, fy = self.LL2localcoords(fx, fy)
                ax.plot_surface(fx, fy, fz)

            if (inputfile != '') and (outputdir != ''):
                for fn in inputfile.split('\n'):
                    for i, (geom, clr) in enumerate(zip(fault_geoms, clrs)):
                        csvname = os.path.splitext(os.path.split(fn)[-1])[0] + f"_fault_{i+1}.csv"
                        csvname = os.path.join(outputdir, csvname)
                        if os.path.isfile(csvname):
                            df = pd.read_csv(csvname)
                            marker = 'o'
                            size = 5
                            
                            xx, yy = df["longitude"], df["latitude"]
                            if localcoords:
                                xx, yy = self.LL2localcoords(xx, yy)                            
                            ax.scatter(xx, yy, df["depth"], c=clr, marker=marker, s=size)

            ax.set_zlim(bottom=0)
            
            if localcoords: 
                # ax.set_box_aspect([1,1,1])
                # set_axes_equal(ax)
                ax.axis('equal')
            
            ax.invert_zaxis()
            ax.set_xlabel("X (km)" if localcoords else "longitude (°)")
            ax.set_ylabel("Y (km)" if localcoords else "latitude (°)")
            ax.set_zlabel("depth (km)")
            self.fault_preview_3D.mpl.figure.tight_layout()
            self.fault_preview_3D.mpl.draw()

        self.__delete_pkl()

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

    def __load_preview(self, preview, table, gdf, color = False, edgecolor = True, isfault = False):
        ax = preview.mpl.figure.axes[0]
        ax.cla()
        try:
            geom_rows = [idx.row() for idx in table.selectionModel().selectedRows()]
            get_colors = lambda n: ["#%06x" % random.randint(0, 0xFFFFFF) for _ in range(n)]
            if geom_rows:
                edgeclrs = get_colors(len(geom_rows)) if edgecolor else (['none'] * len(geom_rows))
                clrs = get_colors(len(geom_rows)) if color else (['none'] * len(geom_rows))
                if isfault:
                    for row, clr in zip(geom_rows, clrs):
                        x, y = gdf.iloc[row].geometry.xy
                        x, y = np.array(x), np.array(y)
                        ax.quiver(x[:-1], y[:-1], x[1:]-x[:-1], y[1:]-y[:-1], 
                                scale_units='xy', angles='xy', scale=1, color=clr)
                gdf.iloc[geom_rows].plot(color=clrs, edgecolor=edgeclrs, 
                                                    linewidth=1, ax=ax)
                lines = [Line2D([0], [0], linestyle="none", marker="s", markersize=10, 
                    markeredgecolor=eclr, markerfacecolor=clr) for clr, eclr in zip(clrs, edgeclrs)]
                ax.legend(lines, geom_rows)
            preview.mpl.draw()
        except: pass

    def _on_btn_area_load_preview_clicked(self):
        self.__load_preview(self.area_preview, self.table_area, self.__gdf_area)
    
    def _on_btn_fault_load_preview_clicked(self):
        self.__load_preview(self.fault_preview, self.table_fault, self.__gdf_fault, 
                            color = True, edgecolor = False, isfault = True)

    def LL2localcoords(self, lons, lats):
        transformer = Transformer.from_crs(4326, 3857)
        x, y = transformer.transform(lats, lons)
        # x = x - np.min(x)
        # y = y - np.min(y)
        return np.array(x)/1000, np.array(y)/1000
    
    def reverse_strike_in_selected_geometries(self):
        geom_rows = [idx.row() for idx in self.table_fault.selectionModel().selectedRows()]
        if geom_rows:
            geom = []
            for row in geom_rows:
                geom.append(LineString(list(self.__gdf_fault.iloc[row].geometry.coords)[::-1]))
            self.__gdf_fault.loc[geom_rows, 'geometry'] = gpd.GeoSeries(geom).values

# Functions from @Mateen Ulhaq and @karlo
def set_axes_equal(ax: plt.Axes):
    """Set 3D plot axes to equal scale.

    Make axes of 3D plot have equal scale so that spheres appear as
    spheres and cubes as cubes.  Required since `ax.axis('equal')`
    and `ax.set_aspect('equal')` don't work on 3D.
    """
    limits = np.array([
        ax.get_xlim3d(),
        ax.get_ylim3d(),
        ax.get_zlim3d(),
    ])
    origin = np.mean(limits, axis=1)
    radius = 0.5 * np.max(np.abs(limits[:, 1] - limits[:, 0]))
    _set_axes_radius(ax, origin, radius)

def _set_axes_radius(ax, origin, radius):
    x, y, z = origin
    ax.set_xlim3d([x - radius, x + radius])
    ax.set_ylim3d([y - radius, y + radius])
    ax.set_zlim3d([z - radius, z + radius])