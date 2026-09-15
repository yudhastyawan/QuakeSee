from custom_openquake import *

inputfile = sys.argv[1]
inputfile2 = sys.argv[2]
outputfile = sys.argv[3]

mle_config = {'magnitude_interval': 0.1 ,
              'Average Type': 'Weighted',
              'reference_magnitude': None }

parser = CsvCatalogueParser(inputfile)
catalogue = parser.read_file()

with open(inputfile2, 'rb') as f:
    comw = pickle.load(f)

b = []
sb = []
a = []
sa = []

for comp in comw:
    b_val, sigma_b, a_val, sigma_a = b_a_value(catalogue, mle_config, np.array([comp]))
    a.append(a_val)
    b.append(b_val)
    sa.append(sigma_a)
    sb.append(sigma_b)

print("time mc a b s_a s_b")
for i, comp in enumerate(comw):
    print(f"{comp[0]:.0f} {comp[1]:.1f} {a[i]:.2f} {b[i]:.2f} {sa[i]:.2f} {sb[i]:.2f}")

with open(outputfile, 'wb') as f:
    pickle.dump([comw, a, b, sa, sb], f)