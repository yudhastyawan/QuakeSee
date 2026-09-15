# QuakeSee
A GUI-based program to see distribution of events, stations, and seismograms available in the earthquake data providers.

## Features
- [x] Download events, station metadata, and waveforms from the open networks
- [x] Load waveforms, plot, and pick phases
- [x] Forward modeling of HVSR
- [x] Download ISC catalogue and convert to OpenQuake catalogue
- [x] Load station metadata (xml) and plot the response and location
- [x] Live recording (show the real-time waveforms) on the open networks
- [x] Set the time, access the recording data, and real-time view from RaspberryShake seismometers
- [x] Calculating Magnitude of Completeness (Mc), b-value from Magnitude-Frequency Distribution (MFD/FMD), and extract the catalogue based on the shape of faults and area (wrapped to Openquake Engine) 

## Installation

QuakeSee is officially distributed as a Conda package, making installation extremely simple across all operating systems (Windows, macOS, Linux).

### Option 1: One-Line Installation (Recommended)
Open your Anaconda Prompt (Windows) or Terminal (macOS/Linux) and run:
```bash
conda create -n quakesee_env -y -c yudha_styawan -c conda-forge quakesee
conda activate quakesee_env
```

### Option 2: Installation from Source
If you prefer to install from source for development purposes:
```bash
git clone https://github.com/yudhastyawan/QuakeSee.git
cd QuakeSee
conda create -n quakesee_env python=3.10
conda activate quakesee_env
pip install -e .
```

## How to Use
Once installed, you can launch the application directly from your terminal by simply typing:
```bash
quakesee
```

### Tips
Change some paths in `user.yaml` file to avoid the warning messages in the console after opening the program. If you do not have "OpenQuake" python, then choose another python path in general.

### Create OQ Inputs
Before using the **Create OQ Inputs** feature, we need to:
1. Install OpenQuake ([download](https://downloads.openquake.org/pkgs/windows/oq-engine/))
2. Open `user.yaml` file, change the contents:
```yaml
path_OQ:
  python: "path/to/openquake/python/executable/file"
  outputdir: "/path/to/output/destination/file/directory"
```
3. Restart the `quakesee` application.

## To-Do Lists
- [x] Expand to a bigger software
- [x] Add a utility to load waveforms and save it as a single file in *.mseed
- [x] Add a utility to modify waveforms data
- [x] Add a utility to plot time vs offsets in loaded waveform data
- [ ] Complete descriptions of "References", "How to Contribute", and "This Program"
- [x] Add a utility to download ISC catalogues
- [x] Convert ISC catalogue to OpenQuake catalogue
- [x] Add a utility to load station/inventory data in *.xml
- [x] Add a utility to plot station/inventory responses
- [ ] Add a utility to conduct HVSR analysis (to do: Inverse Modeling)
- [x] Add a utility to prepare Openquake inputs such as declustering, delimiting data based on sources, a-b values
- [x] Add a utility to pick phases on loaded waveform data
- [x] Add a utility to download and view from raspberry shake seismometers/accelerometers.

## Gallery
<p align="center">
	<img src="src/quakesee/imgs/QuakeSee - 1.png" alt="QuakeSee - 1" width="800"/>
	<br>
	QuakeSee - 1
	<br>
	<img src="src/quakesee/imgs/QuakeSee - 2.png" alt="QuakeSee - 2" width="800"/>
	<br>
	QuakeSee - 2
	<br>
	<img src="src/quakesee/imgs/QuakeSee - 3.png" alt="QuakeSee - 3" width="800"/>
	<br>
	QuakeSee - 3
	<br>
	<img src="src/quakesee/imgs/QuakeSee - 4.png" alt="QuakeSee - 4" width="800"/>
	<br>
	QuakeSee - 4
	<br>	
</p>