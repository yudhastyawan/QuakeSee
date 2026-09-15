from custom_openquake import *

inputfile = sys.argv[1]
inputfile2 = sys.argv[2]
outputfile = sys.argv[3]

fN = lambda a, b, M: np.power(10, a - b*M)


parser = CsvCatalogueParser(inputfile)
catalogue = parser.read_file()

with open(inputfile2, 'rb') as f:
    comw, a, b, sa, sb = pickle.load(f)

rec_table = extract_recurrence_table(catalogue, 0.1)

rec = []
nn = []
rr = []
for i, comp in enumerate(comw):
    rec_table_mc = extract_recurrence_table_Mc(catalogue, 0.1, comp[1], comp[0])
    N = fN(a[i], b[i], rec_table[:-1,0])
    N_Mc = fN(a[i], b[i], rec_table_mc[:-1,0])
    r2 = r_squared(np.log10(rec_table_mc[:-1,4]), np.log10(N_Mc))
    rec.append(rec_table_mc)
    nn.append(N)
    rr.append(r2)

with open(outputfile, 'wb') as f:
    pickle.dump([rec_table, comw, a, b, sa, sb, rec, nn, rr], f)