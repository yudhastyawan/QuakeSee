from custom_openquake import *

inputfile = sys.argv[1]
outputfile = sys.argv[2]

parser = CsvCatalogueParser(inputfile)
catalogue = parser.read_file()

# konfigurasi declustering
declust_config = {'time_distance_window': UhrhammerWindow() ,
                  'fs_time_prop': 1.0}

# fungsi utama declustering
catalogue_declustered = catalogue_declustering(catalogue, declust_config)

# tampilkan jumlah data sebelum dan setelah di-declustered
print("sebelum didekluster: ", len(catalogue['eventID']), " events")
print("setelah didekluster: ", len(catalogue_declustered['eventID']), " events")

key_list = ['eventID','year','month','day','hour','minute','second','longitude',
            'latitude','depth','magnitude','sigmaMagnitude']
catalogue_declustered.write_catalogue(outputfile, key_list=key_list)