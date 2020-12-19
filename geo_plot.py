import set_gdal_pyproj_env_vars_and_logger
from itertools import cycle
from cycler import cycler
import matplotlib.pyplot as plt
import pandas as pd
from geopandas import GeoDataFrame, GeoSeries
import contextily as ctx
from Utils.plogger import Logger
from shapely.geometry import Point
from geo_io import (GeoData, get_date_range, daterange, swath_selection,
                    EPSG_31256_adapted, EPSG_OSM,
                    add_basemap_osm)


MARKERSIZE = 3
MARKERSIZE_ERROR = 7
logger = Logger.getlogger()


def plot_checked_stations():
    _, ax = plt.subplots(figsize=(10, 10))
    color_cycle = cycler('color', 'bgcmyk')  # cycle through primary colors except red which is for error
    gd = GeoData()
    start_date = -1
    while start_date == -1:
        start_date, end_date = get_date_range()

        error_df = pd.DataFrame({'Easting': [], 'Northing': [], 'GP_TODO': []})
    for _date, color in zip(daterange(start_date, end_date), cycle(color_cycle)):
        valid = gd.read_geo_data(_date)
        if valid:
            geo_df = gd.get_geo_df()
            geo_df = geo_df[pd.to_datetime(geo_df['SAVED_TIMESTAMP']).dt.date == _date]
            eastings = geo_df['LocalEasti'].tolist()
            northings = geo_df['LocalNorth'].tolist()
            gp_todo = geo_df['GP_TODO'].tolist()

            assert len(eastings) == len(northings), "check easting/ northing"

            error_df_day = pd.DataFrame({'Easting': eastings, 'Northing': northings, 'GP_TODO': gp_todo})
            error_df_day = error_df_day[error_df_day['GP_TODO'].str.contains('needed')]
            error_df = error_df.append(error_df_day, ignore_index=True)

            colors = [color['color'] for _ in range(len(eastings))]
            geo_point = [Point(xy) for xy in zip(eastings, northings)]
            gdf = GeoDataFrame(crs=EPSG_31256_adapted, geometry=geo_point)
            gdf = gdf.to_crs(f'epsg:{EPSG_OSM}')
            gdf.plot(ax=ax, alpha=0.5, c=colors, markersize=MARKERSIZE,
                     label=_date.strftime("%d %b"))

    # plot the points with errors
    eastings = error_df['Easting'].tolist()
    northings = error_df['Northing'].tolist()
    geo_point = [Point(xy) for xy in zip(eastings, northings)]
    colors = ['r' for _ in range(len(eastings))]
    if colors:
        gdf = GeoDataFrame(crs=EPSG_31256_adapted, geometry=geo_point)
        gdf = gdf.to_crs(f'epsg:{EPSG_OSM}')
        gdf.plot(ax=ax, alpha=0.5, c=colors, markersize=MARKERSIZE_ERROR, label='error')


    _, _, _, swaths_bnd_gdf = gd.filter_geo_data_by_swaths(swaths_only=True)
    swaths_bnd_gdf.crs = EPSG_31256_adapted
    swaths_bnd_gdf = swaths_bnd_gdf.to_crs(f'epsg:{EPSG_OSM}')
    swaths_bnd_gdf.plot(ax=ax, facecolor='none', edgecolor='black')

    # determine the plot area based on extent of swaths_bnd_gdf
    xmin, xmax, ymin, ymax = ax.axis()

    if input('add basemap: [y/n]: ') in ['y', 'Y', 'yes', 'Yes', 'YES']:
        add_basemap_osm(ax)

    # restore original x/y limits
    ax.axis((xmin, xmax, ymin, ymax))


    ax.set_title(f'HDR status check', fontsize=20)
    plt.legend()
    plt.show()


if __name__ == "__main__":
    nl = '\n'
    logger.info(f'{nl}=================================='\
                f'{nl}===>   Running: geo_plot.py   <==='\
                f'{nl}==================================')

    plot_checked_stations()
