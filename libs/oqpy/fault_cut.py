from custom_openquake import *

inputfile = sys.argv[1]
outputfile = sys.argv[2]
outputdir = sys.argv[3]

with open(outputfile, 'rb') as f:
    fault_geoms, fault_props = pickle.load(f)

os.remove(outputfile)

parser = CsvCatalogueParser(inputfile)
catalogue = parser.read_file()

key_list = ['eventID','year','month','day','hour','minute','second','longitude',
            'latitude','depth','magnitude','sigmaMagnitude']

for i, geom in enumerate(fault_geoms):
    line = LineOQ([PointOQ(lon, lat) for lon, lat in zip(*geom)])
    z1, z2, dip, dist = fault_props[i,:]
    m_s = 1
    fault_surface = SimpleFaultSurface.from_fault_data(line, upper_seismogenic_depth=z1, lower_seismogenic_depth=z2, 
                                                       dip=dip, mesh_spacing=m_s)
    selector = CatalogueSelector(catalogue, create_copy = True)
    cat = selector.within_rupture_distance(fault_surface, distance=dist, lower_depth=z2, upper_depth=z1)
    outname = os.path.splitext(os.path.split(inputfile)[-1])[0] + f"_fault_{i+1}.csv"
    cat.write_catalogue(os.path.join(outputdir, outname), key_list=key_list)
