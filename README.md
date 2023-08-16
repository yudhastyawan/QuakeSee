# QuakeSee
A GUI-based program to see distribution of events, stations, and seismograms available in the earthquake data providers

## How to Use
Install the reqired packages in `requirements.txt` and run `quakesee.py` in your Python. Enjoy!

> **Notes:** We use python 3.10

### Detail Instruction

1. Install miniconda/anaconda (Download [miniconda](https://docs.conda.io/en/latest/miniconda.html))
2. Open Anaconda prompt (run as administrator) in Windows / Open terminal in Linux or Mac
3. Make sure Anaconda is active by seeing `(base)`
4. Run command `conda create -n quakesee python=3.10`
5. Run command `conda activate quakesee`
6. [Download](https://github.com/yudhastyawan/QuakeSee/archive/refs/heads/main.zip)/Clone this repository to your computer drive
7. If in a Zip file, extract the contents in one folder
8. Locate Anaconda prompt/Terminal to the extracted folder by command `cd "locate/to/folder"` (For going to a different drive, put the drive name in CMD e.g. `F:` in Windows)
9. Run command `pip install -r requirements.txt`
11. Run command `python quakesee.py`
12. Enjoy!

### Tips
Change some paths in `user.yaml` file to avoid the warning messages in the console after opening the program. If you do not have "OpenQuake" python, then choose another python path in general.

### Create OQ Inputs
Before using the **Create OQ Inputs** feature, we need to:
1. Install OpenQuake ([download](https://downloads.openquake.org/pkgs/windows/oq-engine/))
2. Open `user.yaml` file, change the contents:
```
path_OQ:
  python: "path/to/openquake/python/executable/file"
  outputdir: "/path/to/output/destination/file/directory"
```
3. Run command `python quakesee.py` (see detail instruction)
4. Enjoy!

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
	<img src="/imgs/QuakeSee - 1.png" alt="QuakeSee - 1" width="800"/>
	<br>
	QuakeSee - 1
	<br>
	<img src="/imgs/QuakeSee - 2.png" alt="QuakeSee - 2" width="800"/>
	<br>
	QuakeSee - 2
	<br>
	<img src="/imgs/QuakeSee - 3.png" alt="QuakeSee - 3" width="800"/>
	<br>
	QuakeSee - 3
	<br>
	<img src="/imgs/QuakeSee - 4.png" alt="QuakeSee - 4" width="800"/>
	<br>
	QuakeSee - 4
	<br>	
</p>