"""
Utility functions for parsing input options.

Setting up the area of interest, pre-processing aircraft data
and returning useful satellite parameters.
"""

import os
import numpy as np
from datetime import datetime
import pandas as pd
import scipy.interpolate as interpolate
from pyresample import create_area_def as create_area_def_pyr


def show_usage():
    """Show usage instructions and quit."""
    print("A python aircraft trajectory plotter.")
    print('Call with:')
    print('python Main.py /sat/datadir/ /path/to/traj sat_type\
 scan_type flight_type /out/dir/ tag')
    print('Where sat_type is one of:')
    print('    "AHI" for Himawari')
    print('    "ABI" for GOES-R/S')
    print('    "SEV" for Meteosat Second Generation - HRIT Format')
    print('    "SEVN" for Meteosat Second Generation - NAT Format')
    print('    "AGR" for Fengyun-4A')
    print('And where scan_type is one of:')
    print('    "FD" for Full disk')
    print('    "CONUS" for GOES-16 USA')
    print('    "PACUS" for GOES-17 USA')
    print('    "M1" for GOES-16/17 Mesoscale 1')
    print('    "M2" for GOES-16/17 Mesoscale 2')
    print('    "RSS" for MSG/SEVIRI rapid scan')
    print('And where flight_type is one of:')
    print('    "CSV" for a time/lat/lon CSV file')
    print('    "FR24" for a csv file downloaded from flightradar 24')
    print('Tag specifies a string to attach to output filenames.')
    print('You can also specify additional arguments, in order:')
    print('    An YYYMMDDHHMM string specifying start time')
    print('    An YYYMMDDHHMM string specifying end time')

    quit()


def create_area_def(extent, res):
    """
    Create a pyresample area definition covering the aircraft flightpath.

    Arguments:
        extent - the lat/lon bounding box of the flightpath
                 [lon_0,lon_1,lat_0,lat_1]
        res - the area resolution in degrees
    Returns:
        area_def - the corresponding area definition
    """
    new_extent = [extent[0], extent[2], extent[1], extent[3]]
    area_id = 'temporary_area'
    proj_dict = {'proj': 'eqc'}
    area_def = create_area_def_pyr(area_id, proj_dict,
                                   area_extent=new_extent,
                                   units='deg', resolution=res)

    return area_def


def calc_bounds_sp(ac_pt, lat_bnd, lon_bnd):
    """
    Calculate a scene bounding box from the aircraft point measurement.

    A buffer is added around the edges, given by the bound arguments
    that specify a fraction of the whole scene to bound. For example,
    if the extend is 20 degrees latitude and the latitude buffer is 0.1
    then a 2 degree buffer will be added to the top + bottom
    Arguments:
        ac_traj - the aircraft trajectory dataframe
        lat_bnd - the amount to buffer (top + bottom) on the y axis (lat)
        lon_bnd - the amount to buffer (top + bottom) on the x axis (lon)
    Returns:
        extent - a list of bounds in format min_lon, max_lon, min_lat, max_lat
    """
    lat = ac_pt['Latitude'].mean()
    lon = ac_pt['Longitude'].mean()

    lat0 = lat - lat_bnd
    lat1 = lat + lat_bnd

    lon0 = lon - lon_bnd
    lon1 = lon + lon_bnd

    extent = [lon0, lon1, lat0, lat1]

    return extent


def calc_bounds_traj(ac_traj, lat_bnd, lon_bnd):
    """
    Calculate a scene bounding box from the aircraft trajectory.

    A buffer is added around the edges, given by the bound arguments
    that specify a fraction of the whole scene to bound. For example,
    if the extend is 20 degrees latitude and the latitude buffer is 0.1
    then a 2 degree buffer will be added to the top + bottom
    Arguments:
        ac_traj - the aircraft trajectory dataframe
        lat_bnd - the fraction to buffer (top + bottom) on the y axis (lat)
        lon_bnd - the fraction to buffer (top + bottom) on the x axis (lon)
    Returns:
        extent - a list of bounds in format min_lon, max_lon, min_lat, max_lat
    """
    lat_min = ac_traj['Latitude'].min()
    lat_max = ac_traj['Latitude'].max()
    lat_diff = lat_max - lat_min

    lat0 = lat_min - (lat_diff * lat_bnd)
    lat1 = lat_max + (lat_diff * lat_bnd)

    lon_min = ac_traj['Longitude'].min()
    lon_max = ac_traj['Longitude'].max()
    lon_diff = lon_max - lon_min

    lon0 = lon_min - (lon_diff * lon_bnd)
    lon1 = lon_max + (lon_diff * lon_bnd)

    extent = [lon0, lon1, lat0, lat1]

    return extent


def interp_ac(ac_traj, freq):
    """
    Interpolate the aircraft trajectory onto a fixed time interval.

    This is required to neutralise 'jumps' in the trajectory caused
    by, for example, an aircraft temporarily passing out of ADS-B coverage
    In order for this to work do not pass pre-extrapolated data, such as
    FlightAware's "estimated" positions.
    Arguments:
        ac_traj - the raw aircraft trajectory
        freq - the desired temporal frequency (e.g.: '30s' for 30 seconds)
    Returns:
        ot - the interpolated trajectory (lat/lon/alt only)
    """
    # We need times in unix format
    in_times = ac_traj.index.astype(np.int64) // 10**9

    st_time = ac_traj.index[0]
    # Set start time to 0 seconds, makes it more 'pretty'
    st_time = st_time.replace(second=0)

    out_times = pd.date_range(start=st_time, end=ac_traj.index[-1], freq=freq)
    interp_times = out_times.astype(np.int64) // 10**9

    lats = ac_traj.Latitude.values
    lons = ac_traj.Longitude.values
    alts = ac_traj.Altitude.values

    # Do the interpolation, linear fit is better as cubic can result in
    # divergences near sudden heading changes
    f_lat = interpolate.interp1d(in_times, lats, kind='linear',
                                 fill_value="extrapolate")
    f_lon = interpolate.interp1d(in_times, lons, kind='linear',
                                 fill_value="extrapolate")
    f_alt = interpolate.interp1d(in_times, alts, kind='linear',
                                 fill_value="extrapolate")
    new_lat = f_lat(interp_times)
    new_lon = f_lon(interp_times)
    new_alt = f_alt(interp_times)

    # Put the results into a new Pandas dataframe
    ot = pd.DataFrame()
    ot['Datetime'] = out_times
    ot['Latitude'] = new_lat
    ot['Longitude'] = new_lon
    ot['Altitude'] = new_alt
    ot = ot.set_index('Datetime')

    return ot


def sort_args(inargs):
    """
    Check that arguments are suitable and sorts data into correct format.

    Arguments:
        inargs - list of command line arguments (eg: sys.argv)
    Returns:
        sat_dir - directory that contains satellite data
        flt_fil - the file containing the aircraft trajectory
        sensor - satellite sensor name (AHI, SEV, etc)
        mode - the sensor scanning mode
        flt_type - whether the trajectory is CSV, opensky, numpy pkl, etc
        out_dir - output directory that will contain processed images
        init_t - initial time to process (for skipping start of timeseries)
                 if no command line arg for init_t is given then init_t = None
        end_t - end time to process (for skipping end of timeseries)
                 if no command line arg for end_t is given then end_t = None

    !!!   NOTE: Mode/Sensor combinations are not checked here   !!!
    """
    senlist = ['AHI', 'ABI', 'SEV', 'SEVN', 'AGR']

    init_t = None
    end_t = None

    sat_dir = inargs[1]
    flt_fil = inargs[2]
    sensor = inargs[3]
    mode = inargs[4]
    flt_type = inargs[5]
    out_dir = inargs[6]
    tag = inargs[7]

    if not os.path.isdir(sat_dir):
        print("Incorrect satellite data directory!")
        show_usage()
    if not os.path.isdir(out_dir):
        print("Incorrect output data directory!")
        show_usage()
    if not os.path.isfile(flt_fil):
        print("Incorrect flight trajectory file!")
        show_usage()
    if sensor not in senlist:
        print("Incorrect sensor!")
        show_usage()
    if len(inargs) >= 9:
        dtstr = inargs[8]
        init_t = datetime.strptime(dtstr, "%Y%m%d%H%M")
    if len(inargs) >= 10:
        dtstr = inargs[9]
        end_t = datetime.strptime(dtstr, "%Y%m%d%H%M")

    return sat_dir, flt_fil, sensor, mode, flt_type, out_dir, \
        init_t, end_t, tag


def get_startend(ac_traj, sensor, mode):
    """
    Compute the start and end date for a given aircraft trajectory.

    Arguments:
        ac_traj - the aircraft trajectory dataframe
        sensor - the name of the satellite sensor (AHI, for example)
        mode - the sensor scanning mode (FD for full disk)
    Returns:
        start_time - the datetime of the first aircraft position
        end_time - the datetime of the last aircraft position
        total_ac_time - the total elapsed time for the trajectory
    """
    timestep = sat_timesteps(sensor, mode)
    start_time = get_sat_time(ac_traj.index[0], timestep)
    end_time = get_sat_time(ac_traj.index[len(ac_traj) - 1], timestep)

    tot_ac_time = end_time - start_time
    print("\t-\tAircraft trajectory runs from", start_time, "until", end_time,
          ", which is ", np.round(tot_ac_time.total_seconds()/60), "minutes.")

    return start_time, end_time, tot_ac_time


def get_cur_sat_time(cur_t, sensor, mode):
    """
    Compute the sat start time for a given aircraft trajectory point.

    Arguments:
        cur_t - the time associated with the aircraft trajectory point
        sensor - the name of the satellite sensor (AHI, for example)
        mode - the sensor scanning mode (FD for full disk)
    Returns:
        sat_time - the satellite scan start time
    """
    #print(cur_t)
   # print(sensor)
    #print(mode)
    timestep = sat_timesteps(sensor, mode)
    sat_time = get_sat_time(cur_t, timestep)
    #print(timestep)
    #print(sat_time)
    #quit()

    return sat_time


def get_sat_time(inti, timestep):
    """
    Compute the satellite scan start time for a given input timestamp.

    Arguments:
        inti - the timestamp to compare with
        timestep - the satellite scan time (in minutes)
    Returns:
        outti - the satellite scan start time
    """
    outti = inti
    for i in range(1, len(timestep)):
        tempt = float(inti.minute) + inti.second / 60.
        if timestep[i] > tempt:
            tmin = int(timestep[i-1])
            tsec = (timestep[i-1] - tmin) * 60
            outti = datetime(inti.year, inti.month, inti.day,
                             inti.hour, tmin, int(tsec))
            break
    outti = outti.replace(microsecond=0)

    return outti


def sat_timestep_time(sensor, mode):
    """
    Determine the satellite timestep amount.

    Arguments:
        sensor - the sensor name
        mode - the scanning mode
    Returns:
        A time value in minutes for each scan.
        If unknown sensor/mode combination then returns -1
    """
    if sensor == 'AHI':
        if mode == 'FD':
            return 10
        elif mode == 'MESO':
            return 2.5
        else:
            return -1
    elif sensor == 'ABI':
        if mode == 'FD':
            return 10
        elif mode == 'CONUS':
            return 5
        elif mode == 'PACUS':
            return 5
        elif mode == 'M1':
            return 1
        elif mode == 'M2':
            return 1
        else:
            return 1
    elif sensor == 'SEV' or sensor == 'SEVN':
        if mode == 'FD':
            return 10
        elif mode == 'RSS':
            return 5
        else:
            return -1
    else:
        return -1


def sat_timesteps(sensor, mode):
    """
    Determine the satellite timesteps per hour.

    Arguments:
        sensor - the sensor name
        mode - the scanning mode
    Returns:
        A list of scan start times in the hour (given in minutes)
    """
    if sensor == 'AHI':
        if mode == 'FD':
            return np.linspace(0, 50, 6, dtype=np.int)
        elif mode == 'MESO':
            return np.linspace(0, 60, 25, dtype=np.float32)
        else:
            return -1
    elif sensor == 'ABI':
        if mode == 'CONUS' or mode == 'PACUS':
            return np.linspace(0, 55, 12, dtype=np.int)
        if mode == 'M1' or mode == 'M2':
            return np.linspace(0, 59, 60, dtype=np.int)
    elif sensor == 'SEV' or sensor == 'SEVN':
        if mode == 'FD':
            return np.linspace(0, 50, 6, dtype=np.int)
        if mode == 'RSS':
            return np.linspace(0, 55, 12, dtype=np.int)
    else:
        return -1
    return -1
