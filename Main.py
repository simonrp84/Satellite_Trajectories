"""
A library to overlay aircraft trajectories on satellite images.

Useful for examining incidents such as weather encounters.

Currently supported aircraft data:
    -   Time/Lat/Lon/Alt CSV

Currently supported satellite data:
    -   Himawari
    -   GOES-R/S

See the show_usage() function in Utils.py for call information.


This file contains the main routine for running the library,
main_aircraft_processing(), and an example of how to call it.
Currently an 'opts' list must be passed. In this future this will
become a class, which would be easier to use.

"""

from datetime import datetime
import Data_Load as indata
import Plotting as acplot
import Utils as utils
import logging
import sys
import os

logger = logging.getLogger()
logger.disabled = True

import warnings
warnings.filterwarnings('ignore')


def main_aircraft_processing(opts):
    """Control routine for processing."""
    sat_dir = opts[0]
    flt_fil = opts[1]
    sensor = opts[2]
    flt_typ = opts[3]
    out_dir = opts[4]
    beg_t = opts[5]
    end_t = opts[6]
    mode = opts[7]
    comp = opts[8]
    lat_bnd = opts[9]
    lon_bnd = opts[10]
    sat_cmap = opts[11]
    bg_col = opts[12]
    ac_se_col = opts[13]
    ac_cmap = opts[14]
    ac_mina = opts[15]
    ac_maxa = opts[16]
    ac_pos_col = opts[17]
    txt_col = opts[18]
    txt_size = opts[19]
    txt_pos = opts[20]
    cache_dir = opts[21]
    res = opts[22]
    tag = opts[23]
    linewid = opts[24]
    dotsiz = opts[25]
    singlep = opts[26]

    print("Beginning processing")

    verbose = True

    if (flt_typ == 'CSV'):
        ac_traj = indata.read_aircraft_csv(flt_fil, beg_t, end_t)
    elif (flt_typ == 'FR24'):
        ac_traj = indata.read_aircraft_fr24(flt_fil, beg_t, end_t)
    else:
        print("ERROR: Unsupported flight data type:", flt_typ)
        quit()

    ac_traj2 = utils.interp_ac(ac_traj, '30S')

    if verbose:
        print("\t-\tLoaded aircraft trajectory.")
    if (singlep):
        plot_bounds = utils.calc_bounds_sp(ac_traj, lat_bnd, lon_bnd)
    else:
        plot_bounds = utils.calc_bounds_traj(ac_traj, lat_bnd, lon_bnd)

    n_traj_pts2 = len(ac_traj2)

    area = utils.create_area_def(plot_bounds, res)

    start_t, end_t, tot_time = utils.get_startend(ac_traj, sensor, mode)

    prev_time = datetime(1850, 1, 1, 0, 0, 0)
    old_scn = None
    sat_img = None

    for i in range(2, n_traj_pts2):
        outf = out_dir + str(i-1).zfill(4) + '_' + comp + '_' + tag + '.png'
        if os.path.exists(outf):
            continue
        cur_time = ac_traj2.index[i]
        if verbose:
            print('\t-\tNow processing', cur_time)

        sat_time = utils.get_cur_sat_time(cur_time, sensor, mode)
        if sat_time != prev_time:
            if verbose:
                print('\t-\tLoading satellite data for', sat_time)
            sat_img = indata.load_sat(sat_dir, sat_time, comp,
                                      sensor, plot_bounds, cache_dir, mode)
            if sat_img is None and old_scn is not None:
                sat_img = old_scn
            elif sat_img is None:
                print("ERROR: No satellite data for", sat_time)
            old_scn = sat_img
            prev_time = sat_time
        else:
            if verbose:
                print('\t-\tSatellite data already loaded for', sat_time)

        if verbose:
            print('\t-\tPlotting and saving results')

        fig = acplot.setup_plot(plot_bounds, bg_col, linewid, sat_img[comp].attrs['area'].to_cartopy_crs())

        if sat_img is not None:
            fig = acplot.overlay_sat(fig, sat_img, comp, sat_cmap)

      #  fig = acplot.overlay_startend(fig, ac_traj2, ac_se_col, dotsiz)
        if not singlep:
            fig = acplot.overlay_ac(fig, ac_traj2, i,
                                    ac_cmap, ac_mina, ac_maxa, linewid)
        fig = acplot.add_acpos(fig, ac_traj2, i, ac_pos_col, dotsiz)

        fig = acplot.overlay_time(fig, cur_time, txt_col, txt_size, txt_pos)
        acplot.save_output_plot(outf, fig, 90)
        fig.clf()
        fig.close()

    print("Completed processing")


cache_dir = 'F:/SatPy_CACHE/'

if (len(sys.argv) < 6 or len(sys.argv) > 10):
    utils.show_usage()

s_d, f_f, sen, md, fltt, o_d, b_t, e_t, tag = utils.sort_args(sys.argv)

if b_t == 'None':
    b_t = None
if e_t == 'None':
    e_t = None

inopts = [s_d,  # Sat dir
          f_f,  # Flight file
          sen,  # Sensor
          fltt,  # Flight type
          o_d,  # Output directory
          b_t,  # Initial processing time
          e_t,  # Ending processing time
          md,  # Scanning mode
          #'colorized_ir_clouds',  # Composite mode
          'true_color',  # Composite mode
          0.2,  # Lat multiplier
          0.05,  # Lon multiplier
          'Greys_r',  # Satellite colourmap
          'Red',  # Coastlines colour
          'Red',  # Aircraft start/end position colour
          'viridis',  # Aircraft trajectory colourmap
          1000,  # Aircraft min altitude for colourmap
          38000,  # Aircraft max altitude for colourmap
          'Red',  # Aircraft position colour
          'Red',  # Text colour
          15,  # Text fontsize
          [0.04, 0.92],  # Text position
          cache_dir,  # Cache dir for satpy
          0.003,  # Output map resolution
          tag,  # Tag to include in name of output file, often callsign
          1.0,  # Linewidth for borders and trajectory
          3.0,  # Dot size for start / end and current aircraft position
          False]  # Single point mode, only one aircraft position

main_aircraft_processing(inopts)
