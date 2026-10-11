# Classifying Fish from Echosounder Data

## Background (fish side of things)

Notes from a friend who worked as an acoustics research technician at DFO (calverterik@gmail.com).

`Echosounder`: sends pulses up through the water and records the echoes (DFO's echosounders sit on the seafloor). Anything in the water bounces sound back: fish, 
plankton, etc,. It records at several frequencies at once, usually 4 (I don't know the range). Small things like plankton echo strongly at high frequencies, and fish with swim bladders echo strongly at low ones. 

### Data
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

## File Types

`.01A` file is raw data (I believe over 1 week)

There should be one `.xml` file that defines the instrument set up (frequencies, calibration, pulse lengths?) for a set of `.01A` files. 





