from custom_openquake import *

inputfile = sys.argv[1]
outputfile = sys.argv[2]

parser = CsvCatalogueParser(inputfile)
catalogue = parser.read_file()


rec_table = extract_recurrence_table(catalogue, 0.1)

with open(outputfile, 'wb') as f:
    pickle.dump(rec_table, f)