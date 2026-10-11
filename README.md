# Classifying Fish from Echosounder Data

Note: These are my notes, it's a bit of a rant but it should get you up to date. I'll save this somewhere else later. Current issue is that all of the data is on a 4 TB SSD that I cannot hold but I'll be able to grab a small sample set on Tuesday. See [Hosting the data](#file-types-and-hosting-the-data) for more information. 

## Background (fish side of things)

Notes from a friend who worked as an acoustics research technician at DFO (calverterik@gmail.com).

`Echosounder`: sends pulses up through the water and records the echoes (DFO's echosounders sit on the seafloor). Anything in the water bounces sound back: fish, 
plankton, etc,. It records at several frequencies at once, usually 4 (I don't know the range). Small things like plankton echo strongly at high frequencies, and fish with swim bladders echo strongly at low ones. 

`Echoview`: software DFO uses to analyze echosounder data (we do not have access to this). 
Uses: 
- View echograms (turns raw files into visuals of depth over time) `.01A`
- Cleaning data: removing noise, fixed bottom line, fixed top line, etc
- Labelling: people draw regions around schools and tag them. Files saved as `.evr`

### Focus
The data comes from a fixed echosounder in the Malaspina Strait. It sits in one spot and pings
the water column continuously, so we get a record of what passes through over time.

We're focused on pelagic fish (fish that live in the open water column, not on the bottom).
Some of them have pretty recognizable acoustic signatures:
- Herring
- Salmon
- Juvenile salmon
- Hake, though it's harder to pick out than the others

### The mesopelagic / scattering layer
There's a very distinct layer made up of plankton, small and larval fish, gelatinous animals, and squid.
On an echogram it shows up as a dense cloudy band.

It moves on a daily cycle called **diel vertical migration (DVM)**:
- Day: it sinks deeper
- Night: it rises to shallower water and spreads out

This layer is an important food source for bigger fish, so a lot of fish species follow the same
up and down pattern.

**This matters for us:** during the day the layer sits deep and is easy to tell apart from fish.
At night it rises and spreads out, and the fish come up with it, so everything gets mixed together.
We'll probably start with daytime data.

---

## File Types and Hosting the Data

[Echoview file formats](https://support.echoview.com/WebHelp/Reference/File_Formats/echoview_file_formats.htm)

We have 4 TB of data dating back X? amount of years.

We need: 
- Raw: `.01A`, `.xml`
- Labelled regions: `.evr`, `.evl`

`.01A` file is raw data (I believe over 1 week)
`.xml` config/calibration file that defines the instrument set up (frequencies, calibration, pulse lengths?) for a set of `.01A` files. 
`.ev`  the main Echoview file. It links to the raw `.01A` files and holds all the processing: noise reduction, labelled regions (classes), and the fixed bottom and surface lines 
`.evr` 2D region definitions. It's a text file listing every labelled region as points (time + depth) plus its label
`.evl`line definitions (e.g. the bottom or surface line). Also exported from Echoview as text 

We can only open `.ev` files in Echoview, which we don't have. So if there is only a `.ev` file available we will need
to ask my friend to export the `.evr` files (and ideally `.evl` for the bottom/surface lines). Those are what we can actually read in Python.

The labels `.evr` and the echo data `.01A` are stored in separate files, and the only thing linking them is time. To build training examples, we need to find the raw file that covers each region's time range so we can cut that region out of the echogram and pair it with its label. 

I'll run a script to pull a small sample (a couple of labelled regions and their raw files) off the SSD, so we can build and test things without needing the drive. 


















