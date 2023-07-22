from custom_openquake import *

magnitude_bin_width = 0.1
time_bin_width = 0.1

inputfile = sys.argv[1]
outputfile = sys.argv[2]

parser = CsvCatalogueParser(inputfile)
catalogue = parser.read_file()

mag_bins = np.arange(
            np.min(catalogue.data['magnitude']),
            np.max(catalogue.data['magnitude']) + magnitude_bin_width / 2.,
            magnitude_bin_width)

time_bins = np.arange(
            float(np.min(catalogue.data['year'])),
            float(np.max(catalogue.data['year'])) + 1.,
            float(time_bin_width))

mag_time_dist = catalogue.get_magnitude_time_distribution(
        mag_bins,
        time_bins,
        None,
        None)

with open(outputfile, 'wb') as f:
    pickle.dump([time_bins,mag_bins,mag_time_dist], f)