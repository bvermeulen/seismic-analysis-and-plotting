import contextily as ctx
import pandas as pd
from geopandas import GeoDataFrame
from shapely.geometry import Point
import matplotlib.pyplot as plt
from cycler import cycler
from itertools import cycle
from Utils.plogger import Logger
from geo_io import GeoData, get_date_range, daterange

MARKERSIZE = 3
MARKERSIZE_ERROR = 7
EPSG_31256_adapted = "+proj=tmerc +lat_0=0 +lon_0=16.33333333333333"\
                     " +k=1 +x_0=+500000 +y_0=0 +ellps=bessel "\
                     "+towgs84=577.326,90.129,463.919,5.137,1.474,5.297,2.4232 +units=m +no_defs"


def add_basemap(ax, zoom, url='http://tile.stamen.com/terrain/tileZ/tileX/tileY.png'):
    logger = Logger.getlogger()
    xmin, xmax, ymin, ymax = ax.axis()
    logger.info(f'url: {url}')
    basemap, extent = ctx.bounds2img(xmin, ymin, xmax, ymax, zoom=zoom, url=url)
    ax.imshow(basemap, extent=extent, interpolation='bilinear')
    # restore original x/y limits
    ax.axis((xmin, xmax, ymin, ymax))


def plot_checked_stations():
    fig, ax = plt.subplots(figsize=(10, 10))
    color_cycle = cycler('color', 'bgcmyk')  # cycle through primary colors except red which is for error
    gd = GeoData()
    start_date = -1
    while start_date == -1:
        start_date, end_date = get_date_range()

    error_df = pd.DataFrame({'Easting': [], 'Northing': [], 'GP_TODO': []})
    for _date, color in zip(daterange(start_date, end_date), cycle(color_cycle)):
        valid, geo_df = gd.read_geo_data(_date)
        if valid:
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
            gdf = gdf.to_crs(epsg=3857)
            gdf.plot(ax=ax, alpha=0.5, c=colors, markersize=MARKERSIZE, 
                     label=_date.strftime("%d %b"))

    # plot the points with errors
    eastings = error_df['Easting'].tolist()
    northings = error_df['Northing'].tolist()
    geo_point = [Point(xy) for xy in zip(eastings, northings)]
    colors = ['r' for _ in range(len(eastings))]
    gdf = GeoDataFrame(crs=EPSG_31256_adapted, geometry=geo_point)
    gdf = gdf.to_crs(epsg=3857)
    gdf.plot(ax=ax, alpha=0.5, c=colors, markersize=MARKERSIZE_ERROR, label='error')

    if input('add basemap: [y/n]: ') in ['y', 'Y', 'yes', 'Yes', 'YES']:
        add_basemap(ax, zoom=13)

    plt.legend()    
    plt.show()

if __name__ == "__main__":
    logformat = '%(asctime)s - %(levelname)s - %(message)s'
    Logger.set_logger('geo_plot.log', logformat, 'DEBUG')
    plot_checked_stations()
