import subprocess
import os
import pickle
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np

dirpath = os.path.dirname(__file__)
tmp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tmp")

def embed_pn(inputfile, pklname):
    return os.path.join(tmp_dir, __pn(inputfile,pklname))

def __pn(inputfile, pklname):
    return __n(inputfile) + "_" + pklname

def __n(inputfile):
    return os.path.splitext(os.path.split(inputfile)[-1])[0]

def declustering(pythonbin, inputfile, outputfile, chk = 1):
    pyfile = os.path.join(dirpath, "oqpy", "declustering.py")
    output = run_shell(chk, f'"{pythonbin}" "{pyfile}" "{inputfile}" "{outputfile}"')
    return output.decode()

def MTdensity(pythonbin, inputfile, chk = 1):
    os.makedirs(tmp_dir, exist_ok=True)
    outputfile = os.path.join(tmp_dir, __pn(inputfile,"MT.pkl"))
    pyfile = os.path.join(dirpath, "oqpy", "plot_MTdensity.py")
    output = run_shell(chk, f'"{pythonbin}" "{pyfile}" "{inputfile}" "{outputfile}"')
    return output.decode(), outputfile

def FMD(pythonbin, inputfile, chk = 1):
    os.makedirs(tmp_dir, exist_ok=True)
    outputfile = os.path.join(tmp_dir, __pn(inputfile,"FMD.pkl"))
    pyfile = os.path.join(dirpath, "oqpy", "plot_FMD.py")
    output = run_shell(chk, f'"{pythonbin}" "{pyfile}" "{inputfile}" "{outputfile}"')
    return output.decode(), outputfile

def FMD_AB(pythonbin, inputfile, chk = 1):
    outputfile = os.path.join(tmp_dir, __pn(inputfile,"FMD_AB.pkl"))
    ABfile = os.path.join(tmp_dir, __pn(inputfile,"AB.pkl"))

    pyfile = os.path.join(dirpath, "oqpy", "plot_FMD_AB.py")
    output = run_shell(chk, f'"{pythonbin}" "{pyfile}" "{inputfile}" "{ABfile}" "{outputfile}"')
    return output.decode(), outputfile

def MC(pythonbin, inputfile, chk = 1):
    os.makedirs(tmp_dir, exist_ok=True)
    outputfile = os.path.join(tmp_dir, __pn(inputfile,"MC.pkl"))
    pyfile = os.path.join(dirpath, "oqpy", "m_c.py")
    output = run_shell(chk, f'"{pythonbin}" "{pyfile}" "{inputfile}" "{outputfile}"')
    return output.decode(), outputfile

def ABvalue(pythonbin, inputfile, chk = 1):
    outputfile = os.path.join(tmp_dir, __pn(inputfile,"AB.pkl"))
    MCfile = os.path.join(tmp_dir, __pn(inputfile,"MC.pkl"))

    pyfile = os.path.join(dirpath, "oqpy", "ab_value.py")
    output = run_shell(chk, f'"{pythonbin}" "{pyfile}" "{inputfile}" "{MCfile}" "{outputfile}"')
    return output.decode(), outputfile

def plot_MTdensity(inputfile, outdir, issave):

    outputfile = os.path.join(tmp_dir, __pn(inputfile,"MT.pkl"))
    if not os.path.isfile(outputfile): return

    with open(outputfile, 'rb') as f:
            time_bins, mag_bins, mag_time_dist = pickle.load(f)

    os.remove(outputfile)

    outputfile = os.path.join(tmp_dir, __pn(inputfile,"MC.pkl"))
    if os.path.isfile(outputfile):
        with open(outputfile, 'rb') as f:
            comw = pickle.load(f)

    vmin_val = np.min(mag_time_dist[mag_time_dist > 0.])
    norm_data = LogNorm(vmin=vmin_val, vmax=np.max(mag_time_dist))

    fig, ax = plt.subplots()
    fig.suptitle(__n(inputfile))
    im = ax.pcolor(time_bins,
                mag_bins,
                mag_time_dist.T,
                norm=norm_data)
    
    if os.path.isfile(outputfile):
        start_time, end_time = time_bins[0], time_bins[-1]
        comw = np.array(comw)
        comp = np.column_stack([np.hstack([end_time, comw[:, 0], start_time]),
                                np.hstack([comw[0, 1], comw[:, 1], comw[-1, 1]])])
        ax.step(comp[:-1, 0], comp[1:, 1], linestyle='-',
                where="post", linewidth=3, color='brown')
        
        os.remove(outputfile)

    ax.set_xlabel('Time (year)')
    ax.set_ylabel('Magnitude')
    ax.set_xlim(time_bins[0], time_bins[-1])
    ax.set_ylim(mag_bins[0], mag_bins[-1] + (mag_bins[-1] - mag_bins[-2]))
    fig.colorbar(im, label='Event Count', shrink=0.9, ax=ax)
    if issave:
         outputfile = os.path.join(outdir, __pn(inputfile,"MT.png"))
         fig.savefig(outputfile, dpi=300, bbox_inches ="tight")
         plt.close(fig)

def plot_FMD(inputfile, outdir, issave):
    outputfile = os.path.join(tmp_dir, __pn(inputfile,"FMD.pkl"))
    if not os.path.isfile(outputfile): return

    if os.path.isfile(outputfile):
        with open(outputfile, 'rb') as f:
                rec_table = pickle.load(f)

        os.remove(outputfile)

        fig, ax = plt.subplots()

        ax.plot(rec_table[:-1,0], rec_table[:-1,3], "bo", label="incremental FMD")
        ax.plot(rec_table[:-1,0], rec_table[:-1,4], "ro", label="cumulative FMD")
        plt.semilogy()
        plt.legend()

        if issave:
            outputfile = os.path.join(outdir, __pn(inputfile,"FMD.png"))
            fig.savefig(outputfile, dpi=300, bbox_inches ="tight")
            plt.close(fig) 

def plot_FMD_AB(inputfile, outdir, issave):

    outputfile = os.path.join(tmp_dir, __pn(inputfile,"FMD_AB.pkl"))
    if not os.path.isfile(outputfile): return

    if os.path.isfile(outputfile):
        with open(outputfile, 'rb') as f:
                rec_table, comw, a, b, sa, sb, rec_mc, nn, rr = pickle.load(f)

        os.remove(outputfile)

        nfig = 1
        for comp, a_val, b_val, sigma_a, sigma_b, rec_table_mc, N, r2 in zip(comw, a, b, sa, sb, rec_mc, nn, rr):
            fig = plt.figure()
            fig.suptitle(__n(inputfile))
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

            if issave:
                outputfile = os.path.join(outdir, __pn(inputfile,f"FMD_AB_{nfig}.png"))
                fig.savefig(outputfile, dpi=300, bbox_inches ="tight")
                plt.close(fig)
                nfig += 1

def area_cut(pythonbin, inputfile, outputdir, area_geoms, dict_depth, chk = 1):

    os.makedirs(tmp_dir, exist_ok=True)
    outputfile = os.path.join(tmp_dir, __pn(inputfile,"area_cut.pkl"))
    with open(outputfile, 'wb') as f:
        pickle.dump([area_geoms, dict_depth], f)
    pyfile = os.path.join(dirpath, "oqpy", "area_cut.py")
    output = run_shell(chk, f'"{pythonbin}" "{pyfile}" "{inputfile}" "{outputfile}" "{outputdir}"')
    return output.decode(), outputfile

def fault_cut(pythonbin, inputfile, outputdir, fault_geoms, fault_props, chk = 1):

    os.makedirs(tmp_dir, exist_ok=True)
    outputfile = os.path.join(tmp_dir, __pn(inputfile,"fault_cut.pkl"))
    with open(outputfile, 'wb') as f:
        pickle.dump([fault_geoms, fault_props], f)
    pyfile = os.path.join(dirpath, "oqpy", "fault_cut.py")
    output = run_shell(chk, f'"{pythonbin}" "{pyfile}" "{inputfile}" "{outputfile}" "{outputdir}"')
    return output.decode(), outputfile

def fault_mesh(pythonbin, inputfile, fault_geoms, fault_props, chk = 1):

    os.makedirs(tmp_dir, exist_ok=True)
    outputfile = os.path.join(tmp_dir, __pn(inputfile,"fault_mesh.pkl"))
    with open(outputfile, 'wb') as f:
        pickle.dump([fault_geoms, fault_props], f)
    pyfile = os.path.join(dirpath, "oqpy", "fault_mesh.py")
    output = run_shell(chk, f'"{pythonbin}" "{pyfile}" "{inputfile}" "{outputfile}"')
    return output.decode(), outputfile

def check_shell(pythonbin):
    pyfile = os.path.join(dirpath, "oqpy", "check_shell.py")
    call_process = f'"{pythonbin}" "{pyfile}"'
    output = 0

    try:
        subprocess.check_output(call_process, shell=True)
        output = 1
    except: pass

    if output == 0:
        try:
            subprocess.check_output('arch -arm64 ' + call_process, shell=True)
            output = 2
        except: pass

    return output

def run_shell(chk, call_process):
    if chk == 0: return 0
    if chk == 2: call_process = 'arch -arm64 ' + call_process
    return subprocess.check_output(call_process, shell=True)