import openquake
from openquake.hmtk.parsers.catalogue import *
from openquake.hmtk.seismicity.catalogue import *
from openquake.hmtk.plotting.seismicity.catalogue_plots import *
from openquake.hmtk.seismicity.declusterer.dec_gardner_knopoff import *
from openquake.hmtk.seismicity.declusterer.distance_time_windows import *
from openquake.hmtk.seismicity.selector import *
from openquake.hazardlib.geo.polygon import Polygon as PolyOQ
from openquake.hazardlib.geo.point import Point as PointOQ
from openquake.hazardlib.geo.line import Line as LineOQ
from openquake.hmtk.seismicity.completeness.comp_stepp_1971 import Stepp1971
from openquake.hmtk.seismicity.occurrence.b_maximum_likelihood import BMaxLikelihood
from openquake.hmtk.plotting.seismicity.completeness.plot_stepp_1972 import create_stepp_plot
from openquake.hmtk.seismicity.smoothing.smoothed_seismicity import SmoothedSeismicity
from openquake.hmtk.seismicity.smoothing.kernels.isotropic_gaussian import IsotropicGaussian
from openquake.hazardlib.geo.surface.complex_fault import ComplexFaultSurface
from openquake.hmtk.sources.area_source import mtkAreaSource
from openquake.hmtk.sources.simple_fault_source import mtkSimpleFaultSource
from openquake.hmtk.sources.complex_fault_source import mtkComplexFaultSource
from openquake.hazardlib.mfd.truncated_gr import TruncatedGRMFD
from openquake.hazardlib.pmf import PMF
from openquake.hazardlib.geo.nodalplane import NodalPlane
from openquake.hazardlib.tom import PoissonTOM
from openquake.hmtk.sources.source_model import mtkSourceModel
from openquake.hazardlib.sourcewriter import write_source_model
from openquake.hmtk.seismicity.occurrence.utils import recurrence_table
from shapely.geometry import *
from shapely.ops import *
import os
import numpy as np
import matplotlib.pyplot as plt
from copy import deepcopy
import pickle
import pyproj
import array
import sys
import shutil
import stat
import glob

# sys.path.insert(0, './SHERIFS')
# from SHERIFS import SHERIFS

# folder penyimpanan
# dir_figs = os.path.join(os.getcwd(), 'figs')
# os.makedirs(dir_figs, exist_ok=True)

# dir_json = os.path.join(os.getcwd(), 'xmlfiles')
# os.makedirs(dir_json, exist_ok=True)

def copytree(src, dst, symlinks = False, ignore = None):
    if not os.path.exists(dst):
        os.makedirs(dst)
        shutil.copystat(src, dst)
    lst = os.listdir(src)
    if ignore:
        excl = ignore(src, lst)
        lst = [x for x in lst if x not in excl]
    for item in lst:
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if symlinks and os.path.islink(s):
            if os.path.lexists(d):
                os.remove(d)
            os.symlink(os.readlink(s), d)
            try:
                st = os.lstat(s)
                mode = stat.S_IMODE(st.st_mode)
                os.lchmod(d, mode)
            except:
                pass # lchmod not available
        elif os.path.isdir(s):
            copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)

# membuat colormap diskrit
def get_cmap(n, name='jet'):
    return plt.cm.get_cmap(name, n)

def duplicate_var(var, multiplier):
    res = [var]*multiplier
    return res

def catalogue_to_dict(catalogue):
    idcs = ['eventID','year','month','day','hour',
       'minute','second','longitude','latitude',
       'depth','magnitude','sigmaMagnitude']

    dict_catalogue = dict()
    for idx in idcs:
        if isinstance(catalogue[idx], list): 
            dict_catalogue[idx] = catalogue[idx]
        else:
            dict_catalogue[idx] = catalogue[idx].tolist()
    return dict_catalogue

def catalogue_from_pkl(filename):
    dict_catalogue = open_pkl(filename)
    catalogue = Catalogue.make_from_dict(dict_catalogue)
    for key in catalogue.data.keys():
        if catalogue.data[key] != []:
            if isinstance(catalogue.data[key][0], int) or isinstance(catalogue.data[key][0], float):
                catalogue.data[key] = np.array(catalogue.data[key])
    return catalogue

def catalogue_pkl_to_csv(filename_pkl, filename_csv):
    catalogue = catalogue_from_pkl(filename_pkl)
    catalogue.write_catalogue(filename_csv, key_list=list(catalogue.data.keys()))
            
# save variabel ke pickle file untuk dibuka kembali di file lain
def variable_to_pkl(variabel, filename, protocol=False):
    with open(filename, 'wb') as file:
        if protocol==True:
            pickle.dump(variabel, file, pickle.HIGHEST_PROTOCOL)
        else:
            pickle.dump(variabel, file)          

# save katalog ke pickle file
def catalogue_to_pkl(catalogue, filename=None, dict_faults=None, range_deep=None, type_of=None):
    if type_of == "fault":
        if dict_faults["merged"] != None:
            for idcs, cat in zip(dict_faults["merged"], catalogue["merged"]):
#                 catalogue_to_pkl(cat, "dict_catalogue_fault_"+"_".join([dict_faults["name"][i] for i in idcs])+".pkl")
                catalogue_to_pkl(cat, "dict_catalogue_fault_"+"_".join([dict_faults["name"][idcs[0]], "others"])+".pkl")
        if dict_faults["individual"] != None:
            for idx, cat in zip(dict_faults["individual"], catalogue["individual"]):
                catalogue_to_pkl(cat, "dict_catalogue_fault_"+dict_faults["name"][idx]+".pkl")
    elif type_of == "megathrust":
        for i, cat in enumerate(catalogue):
            catalogue_to_pkl(cat, f"dict_catalogue_megathrust_{i+1}.pkl")
    elif type_of == "shallow background":
        for i, cat in enumerate(catalogue):
            catalogue_to_pkl(cat, f"dict_catalogue_shallow_background_{i+1}.pkl")
    elif type_of == "deep background":
        for i, cat in enumerate(catalogue):
            for j in range(len(range_deep)-1):
                catalogue_to_pkl(
                    cat[j], f"dict_catalogue_deep_background_{i+1}_{range_deep[j]}-{range_deep[j+1]}.pkl"
                )
    elif type_of == None:
        dict_catalogue = catalogue_to_dict(catalogue)
        variable_to_pkl(dict_catalogue, filename)
    else:
        print("type_of harus berada di antara berikut ini:")
        print("['fault', 'megathrust', 'shallow background', 'deep background', None]")

# def catalogue_faults_to_pkl(catalogue, dict_faults):
#     if dict_faults["merged"] != None:
#         for idcs, cat in zip(dict_faults["merged"], catalogue["merged"]):
#             catalogue_to_pkl(cat, "dict_catalogue_fault_"+"_".join([dict_faults["name"][i] for i in idcs])+".pkl")
#     if dict_faults["individual"] != None:
#         for idx, cat in zip(dict_faults["individual"], catalogue["individual"]):
#             catalogue_to_pkl(cat, "dict_catalogue_fault_"+dict_faults["name"][idx]+".pkl")

# def catalogue_megathrusts_to_pkl(catalogue):
#     for i, cat in enumerate(catalogue):
#         catalogue_to_pkl(cat, f"dict_catalogue_megathrust_{i+1}.pkl")

# def catalogue_deep_background_to_pkl(catalogue):
#     for i, cat in enumerate(catalogue):
#         catalogue_to_pkl(cat, f"dict_catalogue_deep_background_{i+1}.pkl")

# def catalogue_shallow_background_to_pkl(catalogue):
#     for i, cat in enumerate(catalogue):
#         catalogue_to_pkl(cat, f"dict_catalogue_shallow_background_{i+1}.pkl")
        
# membuka pickle file
def open_pkl(filename, recursive=False):
    if recursive == False:
        with open(filename, 'rb') as file:
            variable = pickle.load(file)
    else:
        list_variables = glob.glob(filename)
        variable = [open_pkl(var) for var in list_variables]
    return variable

# fungsi untuk mengubah data lon lat pada patahan menjadi poligon
def polygon_from_fault(fault_longitude, fault_latitude, distance=20, inProj="EPSG:4326", outProj="EPSG:3857"):
    distance = distance * 1000
    degree_proj = pyproj.Proj(init=inProj)
    utm_proj = pyproj.Proj(init=outProj)
    
    faultLine_degree = LineString([(x, y) for x, y in zip(fault_longitude, fault_latitude)])
    project = lambda x, y: pyproj.transform(degree_proj, utm_proj, x, y)    
    faultLine_utm = transform(project, faultLine_degree)

    dilated = faultLine_utm.buffer(distance)
    
    project = lambda x, y: pyproj.transform(utm_proj, degree_proj, x, y) 
    dilated_degree = transform(project, dilated)
    x, y = dilated_degree.exterior.xy
    return x, y    

# def polygon_from_fault_deprecated_2(fault_longitude, fault_latitude, distance=20, inProj="EPSG:4326", outProj="EPSG:3857"):
#     distance = distance * 1000
#     degree_proj = pyproj.Proj(init=inProj)
#     utm_proj = pyproj.Proj(init=outProj)
    
#     faultLine_degree = LineString([(x, y) for x, y in zip(fault_longitude, fault_latitude)])
#     project = pyproj.Transformer.from_proj(
#         degree_proj,
#         utm_proj)
    
#     faultLine_utm = transform(project.transform, faultLine_degree)
#     dilated = faultLine_utm.buffer(distance)
    
#     project = pyproj.Transformer.from_proj(
#         utm_proj,
#         degree_proj)
    
#     dilated_degree = transform(project.transform, dilated)
#     x, y = dilated_degree.exterior.xy
#     return x, y    

# def polygon_from_fault_deprecated(fault_longitude, fault_latitude, distance=20):
#     distance = distance * 1000
#     fault1_utm = utm.from_latlon(np.array(fault_latitude), np.array(fault_longitude))
#     input_for_faultLine1 = np.array([fault1_utm[0], fault1_utm[1]]).T.tolist()
#     faultLine1 = LineString(input_for_faultLine1)
#     dilated = faultLine1.buffer(distance)
#     dilated_x, dilated_y = dilated.exterior.xy
#     res_lat, res_lon = utm.to_latlon(np.array(dilated_x.tolist()), np.array(dilated_y.tolist()), fault1_utm[2], fault1_utm[3])
#     return res_lon, res_lat

# polygon coords to shapely polygon
def poly_to_shapelypoly(poly):
    polygon = Polygon(np.array([poly[0], poly[1]]).T)
    return polygon

def shapely_to_OQ_poly(shapely_polygon):
    x, y = shapely_polygon.exterior.xy
    polyOQ1 = PolyOQ([PointOQ(lon, lat) for lon, lat in zip(x, y)])
    return polyOQ1

def copy_cutPoly_cutDepth(catalogue, polygon, lower_depth = None, upper_depth = None):
    selector1 = CatalogueSelector(catalogue, create_copy = True)
    catArea = selector1.within_polygon(polygon)
    selector2 = CatalogueSelector(catArea)
    catAreaDepth = selector2.within_depth_range(lower_depth = lower_depth, upper_depth = upper_depth)
    return catAreaDepth

# membuat area dengan jarak tertentu dari patahan
def create_area_faults(faults, distance=20):
    area_faults = {"merged": None, "individual":None}
    area_faults_coords = {"merged": None, "individual":None}
    if faults["merged"] != None:
        polygon_faults = [
            [
                polygon_from_fault(fault[0], fault[1], distance=distance) for fault in selected
            ] for selected in faults["merged"]
        ]
        shapelypolygon_faults = [
            [
                poly_to_shapelypoly(poly) for poly in selected
            ] for selected in polygon_faults
        ]
        merged_shapely = [unary_union(selected) for selected in shapelypolygon_faults]
        for i, selected in enumerate(merged_shapely):
            tmp_selected = selected
            buff = 0.1
            check_multi = False
            while isinstance(tmp_selected, MultiPolygon):
                list_selected = list(selected)
                unary_selected = unary_union([sel.buffer(buff) for sel in list_selected])
                tmp_selected = unary_selected.buffer(-buff)
                buff += 0.1
                check_multi = True
            if check_multi == True: merged_shapely[i] = tmp_selected
        area_faults["merged"] = [shapely_to_OQ_poly(selected) for selected in merged_shapely]
        area_faults_coords["merged"] = [selected.coords for selected in area_faults["merged"]]
    if faults["individual"] != None:
        polygon_faults = [
            polygon_from_fault(fault[0], fault[1], distance=distance) for fault in faults["individual"]
        ]
        shapelypolygon_faults = [poly_to_shapelypoly(poly) for poly in polygon_faults]
        area_faults["individual"] = [shapely_to_OQ_poly(poly) for poly in shapelypolygon_faults]
        area_faults_coords["individual"] = [selected.coords for selected in area_faults["individual"]]
    return area_faults, area_faults_coords

# membuat katalog dari area fault
def create_catalogue_from_area_faults(catalogue, area_faults, dict_faults=None):
    catalogue_area_faults = {"merged": None, "individual": None}
    catalogue_area_faults["merged_depth"] = dict_faults["merged_depth"]
    catalogue_area_faults["individual_depth"] = dict_faults["individual_depth"]

    if area_faults["merged"] != None:
        catalogue_area_faults["merged"] = [
            copy_cutPoly_cutDepth
            (
                catalogue, selected_area, selected_depth
            ) for selected_area, selected_depth in zip(area_faults["merged"], dict_faults["merged_depth"])
        ]

    if area_faults["individual"] != None:
        catalogue_area_faults["individual"] = [
            copy_cutPoly_cutDepth
            (
                catalogue, selected_area, selected_depth
            ) for selected_area, selected_depth in zip(area_faults["individual"], dict_faults["individual_depth"])
        ]
    return catalogue_area_faults

def catalogue_declustering(catalogue, declust_config):
    declustering = GardnerKnopoffType1()
    cluster_index, cluster_flag = declustering.decluster(catalogue, declust_config)

    selectorCatalogue = CatalogueSelector(catalogue, create_copy = True)
    catalogue_declustered = selectorCatalogue.select_catalogue(cluster_flag == 0)
    return catalogue_declustered

def create_catalogue_megathrusts(catalogue, megathrust_geoms, distance = 20, mesh_spacing=10.):
    catalogue_megathrusts = []
    for geom in megathrust_geoms:
        for tf, idx in zip([True, True, False, False],[1,0,1,0]):
            try:
                geom["upper"].sort(reverse=tf, key=lambda x: x[idx])
                geom["lower"].sort(reverse=tf, key=lambda x: x[idx])
                edges = [
                    LineOQ([PointOQ(*coord) for coord in geom["upper"]]),
                    LineOQ([PointOQ(*coord) for coord in geom["lower"]])
                ]
                megathrustOQ = ComplexFaultSurface.from_fault_data(edges, mesh_spacing=mesh_spacing)
                break
            except:
                pass
        selector2 = CatalogueSelector(catalogue, create_copy = True)
        catalogue_megathrust = selector2.within_rupture_distance(megathrustOQ, distance=distance)
        catalogue_megathrusts.append(catalogue_megathrust)
    return catalogue_megathrusts

def create_catalogue_from_shallow_backgrounds(catalogue, shallow_background_geoms, lower_depth=20):
    poly_shallow_background = [
        PolyOQ([PointOQ(lon, lat) for lon, lat in zip(*geom)]) for geom in shallow_background_geoms
    ]
    
    catalogue_shallow_backgrounds = [
        copy_cutPoly_cutDepth(catalogue, poly, lower_depth) for poly in poly_shallow_background
    ]
    return catalogue_shallow_backgrounds

def create_catalogue_from_deep_backgrounds(catalogue, deep_background_geoms, 
                                           upper_depth=50, increment=100, lower_depth=350):
    range_list = list(range(upper_depth, lower_depth, increment)) + [lower_depth]
    
#     poly_background = [
#         PolyOQ([PointOQ(lon, lat) for lon, lat in zip(*geom)]) for geom in deep_background_geoms if Polygon(np.array(geom).T).is_valid else Polygon(np.array(geom).T).buffer(0).exterior.xy
#     ]
    
    poly_background = []
    for i, geom in enumerate(deep_background_geoms):
        if Polygon(np.array(geom).T).is_valid == False:
            geom = Polygon(np.array(geom).T).buffer(0).exterior.xy
        poly_background.append(PolyOQ([PointOQ(lon, lat) for lon, lat in zip(*geom)]))
    
    catalogue_backgrounds = [
        [
            copy_cutPoly_cutDepth(catalogue, poly, 
                                  lower_depth = range_list[i+1], upper_depth = range_list[i]
                                 ) for i in range(len(range_list)-1)
        ] for poly in poly_background
    ]
    return catalogue_backgrounds, range_list

def magnitude_of_completeness(catalogue, comp_config, mag_range=None):
    completeness_algorithm = Stepp1971()
    old = completeness_algorithm.completeness(catalogue, comp_config)
    if mag_range == None:
        completeness_algorithm.simplify()
    else:
        completeness_algorithm.simplify(mag_range=mag_range)
    completeness_table = completeness_algorithm.completeness_table
    return completeness_table, old

def b_a_value(catalogue, mle_config, completeness_table):
    recurrence = BMaxLikelihood()
    b_val, sigma_b, a_val, sigma_a = recurrence.calculate(catalogue, 
                                                         mle_config, 
                                                         completeness = completeness_table)
    return b_val, sigma_b, a_val, sigma_a

def extract_recurrence_table_Mc(catalogue, dmag, m_c, ctime):
    """
    [Magnitude, Number of Observations, Cumulative Number
    of Observations >= M, Number of Observations
    (normalised to annual value), Cumulative Number of
    Observations (normalised to annual value)]
    """
    end_year = float(catalogue.end_year)
    catalogue = catalogue.data
    mag_eq_tolerance = 1E-5
    id1 = np.logical_and(
                catalogue['year'] >= ctime,
                catalogue['magnitude'] >= (m_c - mag_eq_tolerance))
    return recurrence_table(catalogue['magnitude'][id1],
                              dmag,
                              catalogue['year'][id1],
                              end_year - ctime + 1)

def extract_recurrence_table(catalogue, dmag):
    """
    [Magnitude, Number of Observations, Cumulative Number
    of Observations >= M, Number of Observations
    (normalised to annual value), Cumulative Number of
    Observations (normalised to annual value)]
    """
    catalogue = catalogue.data
    return recurrence_table(catalogue['magnitude'],
                              dmag,
                              catalogue['year'])

def r_squared(y, y_hat):
    y_bar = y.mean()
    ss_tot = ((y-y_bar)**2).sum()
    ss_res = ((y-y_hat)**2).sum()
    return 1 - (ss_res/ss_tot)

def plot_magnitude_time_density_with_Mc(catalogue, completeness_table, magnitude_bin_width, time_bin_width, cmap_dist='Pastel1', cmap_Mc='Dark2'):
    plt.set_cmap(cmap_dist)
    plot_magnitude_time_density(catalogue, magnitude_bin_width, time_bin_width)
    cmap = get_cmap(len(completeness_table[:,0]), cmap_Mc)
    for i, (v, h) in enumerate(zip(completeness_table[:,0],completeness_table[:,1])):
        plt.axvline(v, c=cmap(i), label=f"{v:.0f}, Mc {h:.2f}")
        plt.axhline(h, c=cmap(i))
    plt.legend()

def plot_observed_reccurence_with_Mc(catalogue, completeness_table, completeness_table_old, magnitude_bin_width, cmap_Mc='Dark2'):
    plot_observed_recurrence(catalogue, completeness_table_old, magnitude_bin_width)
    cmap = get_cmap(len(completeness_table[:,0]), cmap_Mc)
    for i, (v, h) in enumerate(zip(completeness_table[:,0],completeness_table[:,1])):
        plt.axvline(h, c=cmap(i), label=f"{v:.0f}, Mc {h:.2f}")
    plt.legend()
    
def remove_events_in_A_from_B(catalogue_A, catalogue_B):
    selector1 = CatalogueSelector(catalogue_A)
    flags = ~np.in1d(catalogue_A.data['eventID'], catalogue_B.data['eventID'])
    unique, counts = np.unique(flags, return_counts=True)
    double_counting = dict(zip(unique, counts)).get(False, 0)
    print("jumlah gempa yang dihapus: ", double_counting)
    catalogue_C = selector1.select_catalogue(flags)
    return catalogue_C

def quick_map(var, color, label=None, ax=None):
    if isinstance(var, PolyOQ):
        x, y = map(list, zip(*var.coords))
        ax.plot(x, y, c=color[0], label=label)
    elif isinstance(var, dict):
        if len(set(var.keys()).intersection(set(["merged", "individual"]))) != 0:
            chk = 0
            if var["merged"] != None:
                for item in var["merged"]:
                    quick_map(item, color, label=(label if chk == 0 else None), ax=ax)
                    chk += 1
            if var["individual"] != None:
                for item in var["individual"]:
                    quick_map(item, color, label=(label if chk == 0 else None), ax=ax)
                    chk += 1
        if len(set(var.keys()).intersection(set(["upper", "lower"]))) != 0:
            tmp1 = deepcopy(var["lower"])
            tmp1.reverse()
            tmp = var["upper"] + tmp1
            item = PolyOQ([PointOQ(xyz[0], xyz[1]) for xyz in tmp])
            quick_map(item, color, label=label, ax=ax)
    elif isinstance(var, list):
        if isinstance(var[0], dict):
            for i, item in enumerate(var):
                quick_map(item, color, label=(label if i == 0 else None), ax=ax)
        elif isinstance(var[0][0], array.array):
            for i, item in enumerate(var):
                if Polygon(np.array(item).T).is_valid == False:
                    item = Polygon(np.array(item).T).buffer(0).exterior.xy
                quick_map(PolyOQ([PointOQ(x, y) for x, y in zip(*item)]), color, label=(label if i == 0 else None), ax=ax)
        elif isinstance(var[0][0], Catalogue):
            for i, item in enumerate(var):
                quick_map(item, color, label=(label if i == 0 else None), ax=ax)
        elif isinstance(var[0], tuple):
            if len(var[0]) == 3:
                x, y, z = map(list, zip(*var))
            elif len(var[0]) == 2:
                x, y = map(list, zip(*var))
            quick_map([x, y], color, label=label, ax=ax)
        elif isinstance(var[0][0], list):
            for i, item in enumerate(var):
                quick_map(item, color, label=(label if i == 0 else None), ax=ax)
        elif isinstance(var[0][0], float):
            ax.plot(var[0], var[1], c=color[0], label=label)
    elif isinstance(var, Catalogue):
        ax.scatter(var["longitude"], var["latitude"], c=color[0], label=label)

def quick_create_maps(list_variables, list_colors, list_labels, map_limit=None, ax=None, figsize=(8,8)):
    fig = None
    if ax == None:
        fig, ax = plt.subplots(figsize=figsize)
    
    if list_variables != None:
        for var, color, label in zip(list_variables, list_colors, list_labels):
            quick_map(var, color, label, ax=ax)

    ax.legend(ncol=3)
    if map_limit != None:
        ax.set_ylim(map_limit[0])
        ax.set_xlim(map_limit[1])
    plt.show()
    return (fig, ax)

def geoms_to_polyOQ(filename, type_of=None):
    geoms = open_pkl(filename)
    if type_of == "fault":
        line = [LineOQ([PointOQ(x, y) for x, y in zip(*geom)]) for geom in geoms['individual']]
        return line
    if type_of == "megathrust":
        megathrust = []
        for geom in geoms:
            megathrust.append(
                [
                    LineOQ([PointOQ(*coord) for coord in geom["upper"]]),
                    LineOQ([PointOQ(*coord) for coord in geom["lower"]])
                ]
            )
        return megathrust
    if type_of == "shallow_background":
        poly = [PolyOQ([PointOQ(x, y) for x, y in zip(*geom)]) for geom in geoms]
        return poly
    if type_of == "deep_background":
        poly = [PolyOQ([PointOQ(x, y) for x, y in zip(*geom)]) for geom in geoms]
        return poly
    return None

def reverse_line(line):
    x = np.flip(np.array([point.longitude for point in line.points]))
    y = np.flip(np.array([point.latitude for point in line.points]))
    return LineOQ([PointOQ(xi, yi) for xi, yi in zip(x, y)])

def plot_line(line, ax = None):
    x = np.array([point.longitude for point in line.points])
    y = np.array([point.latitude for point in line.points])
    if ax == None:
        fig, ax = plt.subplots()
    ax.quiver(x[:-1], y[:-1], x[1:]-x[:-1], y[1:]-y[:-1], scale_units='xy', angles='xy', scale=1)
    ax.set_xlim([x.min(), x.max()])
    ax.set_ylim([y.min(), y.max()])
    return ax

def plot_megathrust(megathrust, ax = None):
    xlim = []
    ylim = []
    if ax == None:
        fig, ax = plt.subplots()
    for line in megathrust:
        x = np.array([point.longitude for point in line.points])
        y = np.array([point.latitude for point in line.points])
        ax.quiver(x[:-1], y[:-1], x[1:]-x[:-1], y[1:]-y[:-1], scale_units='xy', angles='xy', scale=1)
        xlim += [x.min(), x.max()]
        ylim += [y.min(), y.max()]
    ax.set_xlim([min(xlim), max(xlim)])
    ax.set_ylim([min(ylim), max(ylim)])
    return ax

def reverse_line3D(line):
    x = np.flip(np.array([point.longitude for point in line.points]))
    y = np.flip(np.array([point.latitude for point in line.points]))
    z = np.flip(np.array([point.depth for point in line.points]))
    return LineOQ([PointOQ(xi, yi, zi) for xi, yi, zi in zip(x, y, z)])

def reverse_megathrust(megathrust, part_of=None):
    new = megathrust
    if part_of == 'both':
        new[0] = reverse_line3D(megathrust[0])
        new[1] = reverse_line3D(megathrust[1])
        return new
    if part_of == 'upper':
        new[0] = reverse_line3D(megathrust[0])
        return new
    if part_of == 'lower':
        new[1] = reverse_line3D(megathrust[1])
        return new
    return new

# TO DO LIST
# dict_catalogue = open_pkl('dict_catalogue_declustered.pkl')
# cat = Catalogue.make_from_dict(dict_catalogue)
# cat.write_catalogue('catalogue_declustered_1.csv', key_list=list(dict_catalogue.keys()))
# catalogue_declustered.write_catalogue('catalogue_declustered_2.csv', key_list=list(dict_catalogue.keys()))
# print(cat)