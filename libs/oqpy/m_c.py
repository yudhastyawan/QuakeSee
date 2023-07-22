from custom_openquake import *

inputfile = sys.argv[1]
outputfile = sys.argv[2]

comp_config = {'magnitude_bin': 0.1,
                'time_bin': 5. ,
                'increment_lock': True }

parser = CsvCatalogueParser(inputfile)
catalogue = parser.read_file()

completeness_table, _ = magnitude_of_completeness(catalogue, comp_config)

np.set_printoptions(threshold=np.inf, suppress = True)
print(completeness_table)

with open(outputfile, 'wb') as f:
    pickle.dump(completeness_table, f)