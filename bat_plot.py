import set_gdal_pyproj_env_vars_and_logger
from itertools import cycle
import pandas as pd
import matplotlib.pyplot as plt
from cycler import cycler
from geopandas import GeoDataFrame, GeoSeries
import contextily as ctx
from shapely.geometry import Point

from Utils.plogger import Logger
from geo_autoseis import calculate_bat_status
from geo_io import (GeoData, get_date, df_to_excel,
                    EPSG_31256_adapted, EPSG_OSM,
                    add_basemap_osm)

th_high = 15
th_mid = 10
th_low = 0

RED = '#FF0000'
ORANGE = '#FF4F00'
YELLOW = '#FFFF00'
GREEN = '#00FF00'

MARKERSIZE = 3
MARKERSIZE_ERROR = 7

logger = Logger.getlogger()
nl = '\n'


def plot_bat_status(geo_df, swaths_bnd_gdf):
    ''' function to plot the battery status
        Parameters:
        :geo_df: panda datafram with geophone stations data
        :swaths_geo_polygon: shapely polygon of selected swaths
        Returns: None
    '''
    _, ax = plt.subplots(figsize=(10, 10))

    _, _, days_over_threshold = calculate_bat_status(geo_df)

    coordinates = {'1_high': [],
                   '2_mid': [],
                   '3_low': [],
                   '4_ok': [],
                  }
    for index, row in geo_df.iterrows():
        days = days_over_threshold[index]

        if not pd.isnull(days):
            coordinate_point = Point(row['LocalEasti'], row['LocalNorth'])
            if days >= th_high:
                coordinates['1_high'].append(coordinate_point)
            elif days >= th_mid:
                coordinates['2_mid'].append(coordinate_point)
            elif days >= th_low:
                coordinates['3_low'].append(coordinate_point)
            else:
                coordinates['4_ok'].append(coordinate_point)
        else:
            pass


    # run in reversed key order to plot high days last
    bat_colors = (GREEN, YELLOW, ORANGE, RED)
    bat_labels = ('not exceeding', f'> {th_low} days', f'> {th_mid} days',
                  f'> {th_high} days')
    for index, (_, coords_for_index) in enumerate(sorted(list(coordinates.items()),
                                                              key=lambda x:x[0], reverse=True)):
        colors = [bat_colors[index] for _ in range(len(coords_for_index))]
        if colors:
            gdf = GeoDataFrame(crs=EPSG_31256_adapted, geometry=coords_for_index)
            gdf = gdf.to_crs(f'epsg:{EPSG_OSM}')
            gdf.plot(ax=ax, alpha=0.4, c=colors, markersize=MARKERSIZE,
                    label=bat_labels[index])
        else:
            pass # just added so I have not overlooked the else!

    swaths_bnd_gdf = swaths_bnd_gdf.to_crs(f'epsg:{EPSG_OSM}')
    swaths_bnd_gdf.plot(ax=ax, facecolor='none', edgecolor='black')

    # determine the plot area based on extent of swaths_bnd_gdf
    xmin, xmax, ymin, ymax = ax.axis()

    if input('add basemap: [y/n]: ') in ['y', 'Y', 'yes', 'Yes', 'YES']:
        add_basemap_osm(ax)

    # restore original x/y limits
    ax.axis((xmin, xmax, ymin, ymax))
    ax.set_title(f'Bat status - {_date.strftime("%d %b")}', fontsize=20)
    plt.legend()
    plt.show()

if __name__ == "__main__":
    logger.info(f'{nl}=================================='\
                f'{nl}===>   Running: bat_plot.py   <==='\
                f'{nl}==================================')

    gd = GeoData()

    # extract geo data by date
    valid = False
    while not valid:
        _date = get_date()
        valid = gd.read_geo_data(_date)

    swaths, geo_df, _, swaths_bnd_gdf = gd.filter_geo_data_by_swaths(source_boundary=True)

    plot_bat_status(geo_df, swaths_bnd_gdf)
