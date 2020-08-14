"""
Functions for plotting the resulting aircraft and satellite data.

Currently, many assumptions are made (such as the wish to colour-code
the aircraft track by altitude. In the future these will be made more generic/
customisable.
"""

import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from satpy.writers import get_enhanced_image

import numpy as np


def save_output_plot(outname, plot, out_dpi):
    """
    Save the plot object to the desired file, uses tight bounding box.

    Arguments:
        outname - the output filename for saving (format chosen from name)
        plot - the matplotlib object
        out_dpi - the requested pixels per inch of the output file
    Returns:
        nothing
    """
    plt.savefig(outname, bbox_inches='tight', pad_inches=0, dpi=out_dpi)


def setup_plot(extent, bg_col, linewid):
    """
    Initialise the matplotlib output figure.

    This will add a coastline overlay to your image
    Argument:
        extent - desired image extent as lon_min, lon_max, lat_min, lat_max
        bg_col - colour to plot the coastlines
        linewid - the width of the lines to plot coastlines
    Returns:
        plt - the matplotlib axes object for using in plot creation
    """
    ax = plt.axes([0, 0, 1, 1],
                  projection=ccrs.PlateCarree(),
                  facecolor='black')
#    ax.background_patch.set_facecolor('black')
    ax.set_extent(extent, ccrs.Geodetic())
    ax.coastlines(resolution='10m', color=bg_col, linewidth=0.2)
    states_provinces = cfeature.NaturalEarthFeature(
        category='cultural',
        name='admin_1_states_provinces_lines',
        scale='10m',
        facecolor='none',
        edgecolor=bg_col,
        linewidth=0.3)
    ax.add_feature(states_provinces,
                   edgecolor=bg_col,
                   linewidth=0.2)
    ax.add_feature(cfeature.BORDERS,
                   edgecolor=bg_col,
                   linewidth=0.2)
    return plt


def overlay_startend(plt_ax, ac_df, ac_color, dotsize):
    """
    Add a start and end marker to a plot.

    Shows aircraft origin and destination as stars
    Arguments:
        plt_ax - the matplotlib axes object to use for plotting
        ac_df - the aircraft trajectory as a pandas dataframe
        ac_color - colour to plot the markers
        dotsize - the size of the matplotlib marker to display
    Returns:
        plt - the matplotlib plot
    """
    lon0 = ac_df.Longitude[0]
    lat0 = ac_df.Latitude[0]
    lon1 = ac_df.Longitude[len(ac_df)-1]
    lat1 = ac_df.Latitude[len(ac_df)-1]

    plt_ax.plot(lon0, lat0, marker='*', color=ac_color, markersize=dotsize)
    plt_ax.plot(lon1, lat1, marker='*', color=ac_color, markersize=dotsize)
    return plt


def overlay_ac(plt_ax, ac_df, traj_lim, ac_cmap, minalt, maxalt, linesize):
    """
    Add an aircraft trajectory segment to a map plot.

    Arguments:
        plt_ax - the matplotlib axes object to use for plotting
        ac_df - the aircraft trajectory as a pandas dataframe
        traj_lim - the maximum row in the dataframe to use
        ac_cmap - colourmap to plot the trajectory, chosen by altitude
        minalt - minimum altitude in the colourmap
        maxalt - maximum altitude in the colourmap
        linesize - the width of the line used to draw the trajectory
    Returns:
        plt - the matplotlib plot
    """
    cmap = plt.cm.get_cmap(ac_cmap)

    lons = ac_df.Longitude[0: traj_lim+1].values
    lats = ac_df.Latitude[0: traj_lim+1].values
    alts = ac_df.Altitude[0: traj_lim+1].values

    for i in range(1, traj_lim+1):
        alt = (alts[i-1] + alts[i])/2.0
        alt = alt - minalt
        if (alt < 0):
            alt = 0
        if (alt > (maxalt-minalt)):
            alt = maxalt-minalt

        alt = alt / (maxalt - minalt)

        lonp = [lons[i-1], lons[i]]
        latp = [lats[i-1], lats[i]]
        color = cmap(alt)
        plt_ax.plot(lonp, latp, color=color, linewidth=linesize)

    return plt_ax


def add_acpos(plt_ax, ac_df, curpt, ac_color, dotsize):
    """
    Add an aircraft trajectory segment to a map plot.

    Arguments:
        plt_ax - the matplotlib axes object to use for plotting
        ac_df - the aircraft trajectory as a pandas dataframe
        curpt - the current position of the aircraft in the dataframe
        ac_color - colour to plot the trajectory, useful for multiple aircraft
        dotsize - the size of the matplotlib marker to display
    Returns:
        plt_ax - the matplotlib plot
    """
    lon = ac_df.Longitude[curpt]
    lat = ac_df.Latitude[curpt]
    plt_ax.plot(lon, lat, marker='*', color=ac_color, markersize=dotsize*2)

    return plt_ax


def overlay_sat(plt_ax, sat_img, comp_type, sat_cmap):
    """
    Add a satellite image as the map background to a plot.

    Arguments:
        plt_ax - the matplotlib axes object to use for plotting
        sat_img - the image to use, must be specified as a SatPy scene
        sat_cmap - the colourmap to use for the satellite data
    comp_type - the Satpy composite to create (true_color, B03, etc)

    Returns:
        plt_ax - the matplotlib plot
    """
    img = sat_img[comp_type]
    crs = img.attrs['area'].to_cartopy_crs()
    if len(img.shape) > 2:
        # This is for a multiband image, such as true color
        img = get_enhanced_image(sat_img[comp_type]).data
        img = np.swapaxes(img.values, 0, 2)
        img = np.swapaxes(img, 0, 1)
        plt_ax.imshow(img, transform=crs, extent=crs.bounds,
                      origin='upper')
    else:
        # This is for a one-band image: B03, HRV, etc
        mini = np.nanpercentile(sat_img[comp_type], 1)
        maxi = np.nanpercentile(sat_img[comp_type], 99.5)
        plt_ax.imshow(img, transform=crs, extent=crs.bounds,
                      origin='upper', cmap=sat_cmap, vmin=mini, vmax=maxi)

    return plt_ax


def overlay_time(plt_ax, cur_time, txt_col, txt_size, pos):
    """
    Add a timestamp overlay to the map plot in the top left.

    Arguments:
        plt_ax - the matplotlib axes object to use for plotting
        cur_time - the timestamp to display on the image
        txt_col - colour of the text to be written
        txt_size - font size for the text to be written

    Returns:
        plt_ax - the matplotlib plot
    """
    ax = plt_ax.gca()

    dtstr = cur_time.strftime("%Y-%m-%d %H:%M:%S")
    plt_ax.text(pos[0], pos[1], dtstr, fontsize=txt_size,
                transform=ax.transAxes, color=txt_col)

    return plt_ax
