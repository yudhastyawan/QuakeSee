from custom_openquake import *

inputfile = sys.argv[1]
outputfile = sys.argv[2]
outputdir = sys.argv[3]

with open(outputfile, 'rb') as f:
    area_geoms, dict_depth = pickle.load(f)

os.remove(outputfile)

parser = CsvCatalogueParser(inputfile)
catalogue = parser.read_file()

key_list = ['eventID','year','month','day','hour','minute','second','longitude',
            'latitude','depth','magnitude','sigmaMagnitude']

poly_area = [
    PolyOQ([PointOQ(lon, lat) for lon, lat in zip(*geom)]) for geom in area_geoms
]

for i, poly in enumerate(poly_area):
    for z1, z2 in zip(dict_depth["upper depth"], dict_depth["lower depth"]):
        cat = copy_cutPoly_cutDepth(catalogue, poly, lower_depth = z2, upper_depth = z1)
        outname = os.path.split(inputfile)[-1].split('.')[0] + f"_area_{i+1}_{str(z1).replace('.', 'pt')}-{str(z2).replace('.', 'pt')}.csv"
        cat.write_catalogue(os.path.join(outputdir, outname), key_list=key_list)
