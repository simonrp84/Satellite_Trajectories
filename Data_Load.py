'''
Contains functions related to reading aircraft and satellite data formats
Currently supported aircraft data:
    -   EUROCONTROL SO6
    -   Flight data management / QAR output
    -   Generic CSV files
Currently supported satellite data:
    -   Himawari / AHI in Full disk mode
    -   GOES R/S in all modes
    
Satellite data requires the Satpy library.
'''

from pandas import datetime
from datetime import timedelta
from pandas import read_csv, to_datetime
from satpy import Scene
from satpy import find_files_and_readers as ffar
from satpy.utils import debug_on
import Utils as utils
#debug_on()

import warnings

try:
    import eurocontrol_reader as eurordr
except:
    warnings.warn("EUROCONTROL SO6 reader is not available.",
                  warnings.ImportWarning)
try:
    import fdm_data_reader as fdmr
except:
    warnings.warn("Flight Data Management reader is not available.",
                  warnings.ImportWarning)

def dateparse(x):
    return datetime.strptime(x, '%d/%m/%y %H:%M:%S')


def read_aircraft_csv(infile, start_t, end_t):
    '''
    This function will convert a CSV file into a pandas dataframe
    Expected columns are: Datetime, Latitude, Longitude, Altitude
    Where Datetime is in the form Day/Month/Year Hour:Minute:Second
    e.g: 26/05/19 05:36:24, 51.47, -0.4543, 0
    For Ground level Heathrow Airport on 26th May 2019 at 5:36:24am UTC
    Arguments:
        infile - the file containing aircraft trajectory information
        start_t - the desired start time, earlier data is removed
        end_t - the desired ending time, later data is removed
    Returns:
        ac_traj - a pandas dataframe holding the aircraft trajectory
    '''
    ac_traj = read_csv(infile,
                       parse_dates=['Datetime'],
                       date_parser=dateparse)
    
    if (start_t != None):
        ac_traj = ac_traj[ac_traj['Datetime'] >= start_t]
    if (end_t != None):
        ac_traj = ac_traj[ac_traj['Datetime'] <= end_t]
    ac_traj = ac_traj.set_index('Datetime')
    ac_traj.index = to_datetime(ac_traj.index)
    
    return ac_traj


def read_aircraft_fdm(infile, start_t, end_t):
    '''
    This function will convert a FDM file (EK format) into a pandas dataframe
    Currently only the date/time, position and altitude are imported.
    Arguments:
        infile - the file containing aircraft trajectory information
        start_t - the desired start time, earlier data is removed
        end_t - the desired ending time, later data is removed
    Returns:
        ac_traj - a pandas dataframe holding the aircraft trajectory
    '''
    try:
        ac_traj = fdmr.read_ekr(infile, start_t, end_t)
    except:
        print("ERROR: FDM Reader is unavailable.")
        raise ImportError("FDM reader not found")
    
    return ac_traj


def read_aircraft_euro(infile, start_t, end_t):
    '''
    This function will convert a EUROCONTROL SO6 file into a pandas dataframe
    Currently only the date/time, position and altitude are imported.
    Eventually this will be replaced with Xavier Olive's 'traffic' library.
    Arguments:
        infile - the file containing aircraft trajectory information
        start_t - the desired start time, earlier data is removed
        end_t - the desired ending time, later data is removed
    Returns:
        ac_traj - a pandas dataframe holding the aircraft trajectory
    '''
    try:
        ac_traj = eurordr.read_so6(infile, start_t, end_t)
    except:
        print("ERROR: SO6 Reader is unavailable.")
        raise ImportError("SO6 reader not found")
    
    return ac_traj


def load_sat(indir, in_time, comp_type, sensor, area_def, cache_dir, mode):
    '''
    This is a wrapper for loading and resampling satellite data, it chooses
    which load routines to use based upon the sensor type.
    Arguments:
        indir - directory holding the satellite data
        in_time - a datetime indicating the scene start time in UTC
        comp_type - the Satpy composite to create (true_color, B03, etc)
        sensor - The sensor name, such as "AHI"
        area_def - the region to resample the data to (covering, f.ex trajectory)
        cache_dir - directory used by SatPy for cache, speeds up GEO resampling
        mode - the scanning mode, 'FD' for full disk, 'CONUS', 'RSS', etc
    Returns:
        sat_data - a remapped satellite data field / composite
    '''
    timedelt = utils.sat_timestep_time(sensor, mode)
    if (sensor == "AHI"):
        try:
            tmp_scn = load_himawari(indir, in_time, comp_type, timedelt)
        except ValueError:
            print("ERROR: No satellite data available for",in_time)
            return None
    elif (sensor == "ABI"):
        try:
            tmp_scn = load_goes(indir, in_time, comp_type, timedelt)
        except ValueError:
            print("ERROR: No satellite data available for",in_time)
            return None
    else:
        print("Currently only Himawari is supported.")
        quit()

    scn = tmp_scn.resample(area_def, cache_dir=cache_dir)
    return scn

def load_himawari(indir, in_time, comp_type, timedelt):
    '''
    This function will load a Himawari/AHI scene as given by img_time
    img_time should be the *start* time for the scan, as the ending time
    will be automatically defined from this using timedelt

    The image will be loaded with Satpy, return value is a cartopy object
    
    Arguments:
        indir - directory holding the Himawari data in HSD (unzipped) format
        img_time - a datetime indicating the scene start time in UTC
        comp_type - the Satpy composite to create (true_color, B03, etc)
        timedelt - the scanning time delta (10 min for full disk AHI)
    Returns:
        sat_data - the satellite data object, unresampled
    '''
    files = ffar(start_time=in_time,
                 end_time=in_time + timedelta(minutes=timedelt-1),
                 base_dir=indir,
                 reader='ahi_hsd')

    scn = Scene(sensor='ahi_hsd', filenames=files)
    scn.load([comp_type])

    return scn
    

def load_goes(indir, in_time, comp_type, timedelt):
    '''
    This function will load a GOES/ABI scene as given by img_time
    img_time should be the *start* time for the scan, as the ending time
    will be automatically defined from this using timedelt

    The image will be loaded with Satpy, return value is a cartopy object

    Arguments:
        indir - directory holding the GOES data in netcdf format
        img_time - a datetime indicating the scene start time in UTC
        comp_type - the Satpy composite to create (true_color, C03, etc)
        timedelt - the scanning time delta (10 min for full disk ABI)
    Returns:
        sat_data - the satellite data object, unresampled
    '''
    files = ffar(start_time=in_time,
                 end_time=in_time + timedelta(minutes=timedelt-1),
                 base_dir=indir,
                 reader='abi_l1b')

    scn = Scene(sensor='abi_l1b', filenames=files)
    scn.load([comp_type])

    return scn
