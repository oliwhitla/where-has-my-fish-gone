
import echopype as ep
import matplotlib.pyplot as plt
import pvlib
import pandas as pd
import glob


"""
By Ali Stein-Gagnon for CSC 475 Fall 2026

Much of this code was adapted from the Echopype documentation:
https://echopype.readthedocs.io/en/latest/convert.html

Mostly from the raw data processing and visualization sections.

Purpose and KPIs:
1. Calculate solar elevation using ping time and mooring coordinates.
2. Calculate dB differencing between the two AZFP channels.
3. Visualize calibrated backscatter and frequency differences.
4. Seperates daytime hours.

TODO: Masking for fishes, saving to netcdf files
"""

# --------------------------------------------------
# MANUAL CONFIGURATION VARIABLES
# --------------------------------------------------

# Variables that need to be changed depending on the deployment/date
# IMPORTANT each 01A file represents an hour of a day, if you want to look at a whole day combine each hour 
# eg. where-has-my-fish-gone/data/2025-03-01_MalaspinaStrait/2025-03-01_MalaspinaStrait/AZFP/55158/DATA/202602/260228*.01A
RAW_DATA_PATH = r""

# EP requires an XML to create an ed object
# This will be the XML that best corresponds to the date of your 01A files
XML_FILE_PATH = r""
# csv metadata path
METADATA_PATH = r""

YEAR_MONTH = "2026-02"

# Deployment coordinates
# Best these remain hardcoded as I took them from the R file and they shouldnt change for all of the Malaspina data
LATITUDE = 48.37295
LONGITUDE = 125.8798333

# AZFP channel identifiers
CHANNEL_67 = "55158-67-1"
CHANNEL_125 = "55158-125-2"

# Environmental parameters
SALINITY = 30  # PSU - currently made but it needs to be calculated from the metadata

# Daytime filtering (hourly files)
START_HOUR = 5
END_HOUR = 20


# --------------------------------------------------
# LOAD AND COMBINE RAW AZFP FILES
# --------------------------------------------------

def load_echo_files():

    # Find all AZFP .01A files
    echo_files = sorted(glob.glob(RAW_DATA_PATH))

    # Onlh use files between 5 AM and 8 PM
    # We could change this to more approproate hrs
    echo_files = [
        file for file in echo_files
        if START_HOUR <= int(file[-6:-4]) < END_HOUR
    ]

    print(f"Number of echo files: {len(echo_files)}")

    if not echo_files:
        raise FileNotFoundError("No AZFP files found. Check RAW_DATA_PATH.")

    ed_list = []

    for echo_file in echo_files:
        print(f"Opening: {echo_file}")

        ed = ep.open_raw(
            echo_file,
            sonar_model="AZFP",
            xml_path=XML_FILE_PATH
        )

        ed_list.append(ed)

    print("Files opened:", len(ed_list))

    print("Combining EchoData files...")

    combined_ed = ep.combine_echodata(
        echodata_list=ed_list
    )

    return combined_ed, ed_list


# --------------------------------------------------
# GET ENVIRONMENTAL PARAMETERS
# --------------------------------------------------

def get_environmental_parameters():

    metadata_df = pd.read_csv(METADATA_PATH)

    mean_sea_pressure = float(
        metadata_df.loc[
            metadata_df["year_month"] == YEAR_MONTH,
            "mean_sea_pressure"
        ].iloc[0]
    )

    env_params = {
        "salinity": SALINITY,
        "pressure": mean_sea_pressure
    }

    return env_params


# --------------------------------------------------
#  BACKSCATTER
# --------------------------------------------------

def calculate_backscatter(combined_ed, env_params):

    print("Calculating volume backscattering strength (Sv)...")

    ds_Sv = ep.calibrate.compute_Sv(
        combined_ed,
        env_params=env_params
    )

    return ds_Sv


# --------------------------------------------------
# CALCULATE SOLAR ELEVATION
# --------------------------------------------------

def calculate_solar_elevation(ds_Sv):

    ping_times = pd.DatetimeIndex(ds_Sv["ping_time"].values)

    if ping_times.tz is None:
        ping_times = ping_times.tz_localize("UTC")

    # Calculate solar position
    solar_position = pvlib.solarposition.get_solarposition(
        time=ping_times,
        latitude=LATITUDE,
        longitude=LONGITUDE
    )

    # Plot solar elevation
    plt.figure(figsize=(12, 5))

    plt.plot(
        ping_times,
        solar_position["apparent_elevation"],
        marker=".",
        markersize=2,
        linestyle="-"
    )

    plt.xlabel("Ping Time (UTC)")
    plt.ylabel("Solar Elevation (degrees)")
    plt.title("Solar Elevation at Each AZFP Ping")
    plt.xticks(rotation=45)
    plt.grid()
    plt.tight_layout()
    plt.show()

    return solar_position


# --------------------------------------------------
# CALCULATE FREQUENCY DIFFERENCE
# --------------------------------------------------

def calculate_frequency_difference(ds_Sv):

    Sv_67 = ds_Sv["Sv"].sel(channel=CHANNEL_67)
    Sv_125 = ds_Sv["Sv"].sel(channel=CHANNEL_125)

    Sv_difference = Sv_125 - Sv_67

    # Plot dB difference
    Sv_difference.plot(
        x="ping_time",
        figsize=(10, 7),
        vmin=-15,
        vmax=15,
        cmap="RdBu_r"
    )

    plt.title("AZFP Frequency Difference (125 - 67 kHz)")
    plt.show()

    return Sv_difference


# --------------------------------------------------
# PLOT BACKSCATTER FOR EACH CHANNEL
# --------------------------------------------------

def plot_backscatter(ds_Sv):

    ds_Sv["Sv"].plot(
        x="ping_time",
        row="channel",
        figsize=(10, 7),
        vmin=-100,
        vmax=-30,
        cmap="jet"
    )

    plt.show()
    plt.close("all")


# --------------------------------------------------
# MAIN PROCESSING
# --------------------------------------------------

def main():

    # Load and combine the 01A files
    combined_ed, ed_list = load_echo_files()

    env_params = get_environmental_parameters()

    ds_Sv = calculate_backscatter(combined_ed, env_params)

    #TODO: Save the calibrated backscatter netcdf file(s) to outputs. Named per day or per week

    # IMPORTANT release the ed objects or there will be 100 errors
    del combined_ed
    del ed_list

    solar_position = calculate_solar_elevation(ds_Sv)

    Sv_difference = calculate_frequency_difference(ds_Sv)

    plot_backscatter(ds_Sv)

    print("AZFP processing complete.")


if __name__ == "__main__":
    main()
