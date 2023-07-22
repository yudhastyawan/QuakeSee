import subprocess
import os
import pickle
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np

dirpath = os.path.dirname(__file__)

def declustering(pythonbin, inputfile, outputfile):
    pyfile = os.path.join(dirpath, "oqpy", "declustering.py")
    output = subprocess.check_output(f'arch -arm64 "{pythonbin}" "{pyfile}" "{inputfile}" "{outputfile}"', shell=True)
    return output.decode()

def MTdensity(pythonbin, inputfile):
    tmp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    outputfile = os.path.join(tmp_dir, "MT.pkl")
    pyfile = os.path.join(dirpath, "oqpy", "plot_MTdensity.py")
    output = subprocess.check_output(f'arch -arm64 "{pythonbin}" "{pyfile}" "{inputfile}" "{outputfile}"', shell=True)
    return output.decode(), outputfile

def FMD(pythonbin, inputfile):
    tmp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    outputfile = os.path.join(tmp_dir, "FMD.pkl")
    pyfile = os.path.join(dirpath, "oqpy", "plot_FMD.py")
    output = subprocess.check_output(f'arch -arm64 "{pythonbin}" "{pyfile}" "{inputfile}" "{outputfile}"', shell=True)
    return output.decode(), outputfile

def FMD_AB(pythonbin, inputfile):
    tmp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    outputfile = os.path.join(tmp_dir, "FMD_AB.pkl")
    pyfile = os.path.join(dirpath, "oqpy", "plot_FMD_AB.py")
    output = subprocess.check_output(f'arch -arm64 "{pythonbin}" "{pyfile}" "{inputfile[0]}" "{inputfile[1]}" "{outputfile}"', shell=True)
    return output.decode(), outputfile

def MC(pythonbin, inputfile):
    tmp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    outputfile = os.path.join(tmp_dir, "MC.pkl")
    pyfile = os.path.join(dirpath, "oqpy", "m_c.py")
    output = subprocess.check_output(f'arch -arm64 "{pythonbin}" "{pyfile}" "{inputfile}" "{outputfile}"', shell=True)
    return output.decode(), outputfile

def ABvalue(pythonbin, inputfile):
    tmp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    outputfile = os.path.join(tmp_dir, "AB.pkl")
    pyfile = os.path.join(dirpath, "oqpy", "ab_value.py")
    output = subprocess.check_output(f'arch -arm64 "{pythonbin}" "{pyfile}" "{inputfile[0]}" "{inputfile[1]}" "{outputfile}"', shell=True)
    return output.decode(), outputfile

def plot_MTdensity(outputfile):

    if np.any([not os.path.isfile(o) for o in outputfile]): return

    with open(outputfile[0], 'rb') as f:
            time_bins, mag_bins, mag_time_dist = pickle.load(f)

    os.remove(outputfile[0])

    if len(outputfile) == 2:
        with open(outputfile[1], 'rb') as f:
            comw = pickle.load(f)
    
        os.remove(outputfile[1])

    vmin_val = np.min(mag_time_dist[mag_time_dist > 0.])
    norm_data = LogNorm(vmin=vmin_val, vmax=np.max(mag_time_dist))

    fig, ax = plt.subplots()
    im = ax.pcolor(time_bins,
                mag_bins,
                mag_time_dist.T,
                norm=norm_data)
    
    if len(outputfile) == 2:
        start_time, end_time = time_bins[0], time_bins[-1]
        comw = np.array(comw)
        comp = np.column_stack([np.hstack([end_time, comw[:, 0], start_time]),
                                np.hstack([comw[0, 1], comw[:, 1], comw[-1, 1]])])
        ax.step(comp[:-1, 0], comp[1:, 1], linestyle='-',
                where="post", linewidth=3, color='brown')

    ax.set_xlabel('Time (year)')
    ax.set_ylabel('Magnitude')
    ax.set_xlim(time_bins[0], time_bins[-1])
    ax.set_ylim(mag_bins[0], mag_bins[-1] + (mag_bins[-1] - mag_bins[-2]))
    fig.colorbar(im, label='Event Count', shrink=0.9, ax=ax)

def plot_FMD(outputfile):
    if os.path.isfile(outputfile):
        with open(outputfile, 'rb') as f:
                rec_table = pickle.load(f)

        os.remove(outputfile)

        fig, ax = plt.subplots()

        ax.plot(rec_table[:-1,0], rec_table[:-1,3], "bo", label="incremental FMD")
        ax.plot(rec_table[:-1,0], rec_table[:-1,4], "ro", label="cumulative FMD")
        plt.semilogy()
        plt.legend()

def plot_FMD_AB(outputfile):
    if os.path.isfile(outputfile):
        with open(outputfile, 'rb') as f:
                rec_table, comw, a, b, sa, sb, rec_mc, nn, rr = pickle.load(f)

        os.remove(outputfile)

        for comp, a_val, b_val, sigma_a, sigma_b, rec_table_mc, N, r2 in zip(comw, a, b, sa, sb, rec_mc, nn, rr):
            fig = plt.figure()
            ax = fig.add_axes([0.1, 0.1, 0.5, 0.75])

            ax.plot(rec_table[:-1,0], rec_table[:-1,3], "b+", label="incremental FMD")
            ax.plot(rec_table[:-1,0], rec_table[:-1,4], "r+", label="cumulative FMD")

            ax.plot(rec_table_mc[:-1,0], rec_table_mc[:-1,3], "bo", label="incremental FMD\n(limited by Mc)")
            ax.plot(rec_table_mc[:-1,0], rec_table_mc[:-1,4], "ro", label="cumulative FMD\n(limited by Mc)")

            ax.plot(rec_table[:-1,0], N, c='black', 
                    label=f"$log(N) = a - bM$\nb = {b_val:.2f}\na = {a_val:.2f}\n"+ \
                    f"$\sigma_b$ = {sigma_b:.2f}\n$\sigma_a$ = {sigma_a:.2f}\n$R^2$ = {r2:.2f}"
                    )

            ax.axvline(comp[1], c="green", label=f"Mc = {comp[1]:.1f}\nyear = {int(comp[0])}")
            ax.set_ylabel("Annual Rate (1/year)", fontname='Times New Roman', fontsize=12)
            ax.set_xlabel("Magnitude ($M_W$)", fontname='Times New Roman', fontsize=12)
            plt.yticks(fontname = "Times New Roman", fontsize=12)
            plt.xticks(fontname = "Times New Roman", fontsize=12)
            L = ax.legend(bbox_to_anchor=(1.05, 1.0), loc='upper left', labelspacing = 1)
            plt.setp(L.texts, fontname='Times New Roman', fontsize=12)
            plt.semilogy()