stat_list = ["BBJI", "BKNI", "GSI", "LHMI", "MNAI", "PMBI", "SMRI", "UGM"]

st = wave_data["waveforms"]

if st != None:
    for i in range(len(st)):
        if st[i].stats.station in stat_list:
            print(st[i].stats.station)
            st[i].stats.network = "GE"

_wave._LoadDataWaveforms__base_waveforms = wave_data["waveforms"].copy()