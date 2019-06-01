'''
This library overlays aircraft trajectories onto satellite images.
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

'''

from datetime import datetime

import Utils as utils
import Data_Load as indata
import pandas as pd
import Plotting as acplot
import sys

def main_aircraft_processing(opts):

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

    print("Beginning processing")

    if (flt_typ == 'CSV'):
        ac_traj = indata.read_aircraft_csv(flt_fil, beg_t, end_t)
        
    ac_traj2 = utils.interp_ac(ac_traj, '30S')
        
    print("\t-\tLoaded aircraft trajectory.")

    plot_bounds = utils.calc_bounds(ac_traj, lat_bnd, lon_bnd)

    n_traj_pts = len(ac_traj)
    n_traj_pts2 = len(ac_traj2)

    area = utils.create_area_def(plot_bounds, res)

    start_t, end_t, tot_time = utils.get_startend(ac_traj, sensor, mode)

    prev_time = datetime(1850,1,1,0,0,0)
    old_scn = None
    sat_img = None

    for i in range(2,n_traj_pts2):
        cur_time = ac_traj2.index[i]
        print('\t-\tNow processing', cur_time)

        sat_time = utils.get_cur_sat_time(cur_time, sensor, mode)
        if (sat_time != prev_time):
            print('\t-\tLoading satellite data for', sat_time)
            sat_img = indata.load_sat(sat_dir, sat_time, comp,
                                      sensor, area, cache_dir, mode)
            if (sat_img == None and old_scn != None):
                sat_img = old_scn
            elif (sat_img == None):
                print("ERROR: No satellite data for",sat_time)
            old_scn = sat_img
            prev_time = sat_time
        else:
            print('\t-\tSatellite data already loaded for', sat_time)
        
        print('\t-\tPlotting and saving results')
        fig = acplot.setup_plot(plot_bounds, bg_col)
        
        if (sat_img != None):
            fig = acplot.overlay_sat(fig, sat_img, comp, sat_cmap)
        
        fig = acplot.overlay_startend(fig, ac_traj2, ac_se_col)
        fig = acplot.overlay_ac(fig, ac_traj2, i, ac_cmap, ac_mina, ac_maxa)
        fig = acplot.add_acpos(fig, ac_traj2, i, ac_pos_col)
        
        fig = acplot.overlay_time(fig, cur_time, txt_col, txt_size, txt_pos)
        acplot.save_output_plot(out_dir+str(i-1).zfill(4)+'_'+comp+'.png', fig, 600)
        fig.clf()
        fig.close()

    print("Completed processing")

cache_dir = '/network/aopp/apres/users/proud/Progs/SATPY_Cache_DIR/'

if (len(sys.argv) < 6 or len(sys.argv) > 8):
    utils.show_usage()

sat_dir, flt_fil, sensor, mode, flt_typ, out_dir, beg_t, end_t = utils.sort_args(sys.argv)

inopts = [sat_dir, # Sat dir
        flt_fil, # Flight file
        sensor, # Sensor
        flt_typ, # Flight type
        out_dir, # Output directory
        beg_t, # Initial processing time
        end_t, # Ending processing time
        'FD', # Scanning mode
        'B03', # Composite mode
        0.05, # Lat multiplier
        0.5, # Lon multiplier
        'Greys_r', # Satellite colourmap
        'Red', # Coastlines colour
        'Green', # Aircraft start/end position colour
        'viridis', # Aircraft trajectory colourmap
        1000, # Aircraft min altitude for colourmap
        35000, # Aircraft max altitude for colourmap
        'Green', # Aircraft position colour
        'Cyan', # Text colour
        7, # Text fontsize
        [0.02, 0.98], # Text position
        cache_dir, # Cache dir for satpy
        0.005] # Output map resolution
        
print(len(inopts))
        
main_aircraft_processing(inopts)
