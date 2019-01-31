import contextily as ctx
import pandas as pd
from geopandas import GeoDataFrame, GeoSeries
from shapely.geometry import Point
import matplotlib.pyplot as plt
from cycler import cycler
from itertools import cycle
from Utils.plogger import Logger
from geo_io import GeoData 
from geo_autoseis_revised import calculate_bat_status

th_high = 15
th_mid = 10
th_low = 0

RED = '#FF0000'
ORANGE = '#FF4F00'
YELLOW = '#FFFF00'
GREEN = '#00FF00'

MARKERSIZE = 3
MARKERSIZE_ERROR = 7
EPSG_31256_adapted = "+proj=tmerc +lat_0=0 +lon_0=16.33333333333333"\
                     " +k=1 +x_0=+500000 +y_0=0 +ellps=bessel "\
                     "+towgs84=577.326,90.129,463.919,5.137,1.474,5.297,2.4232 +units=m +no_defs"
EPSG_basemap = 3857                        
logger = Logger.getlogger()

def add_basemap(ax, zoom, url='http://tile.stamen.com/terrain/tileZ/tileX/tileY.png'):
    xmin, xmax, ymin, ymax = ax.axis()
    logger.info(f'url: {url}')
    basemap, extent = ctx.bounds2img(xmin, ymin, xmax, ymax, zoom=zoom, url=url)
    ax.imshow(basemap, extent=extent, interpolation='bilinear')
    # restore original x/y limits
    ax.axis((xmin, xmax, ymin, ymax))


def plot_bat_status(geo_df, swaths_geo_polygon):
    ''' function to plot the battery status
        Parameters:
        :geo_df: panda datafram with geophone stations data
        :swaths_geo_polygon: shapely polygon of selected swaths
        Returns: None
    '''
    _, ax = plt.subplots(figsize=(10, 10))

    _, _, days_over_threshold = calculate_bat_status(geo_df)
    
    coordinates = {'high': [],
                   'mid': [], 
                   'low': [],
                   'ok': [],
                  }
    for index, row in geo_df.iterrows():
        days = days_over_threshold[index]
        coordinate = (row['LocalEasti'], row['LocalNorth'])

        if pd.isnull(days):
            continue
        else:
            pass

        if days >= th_high:
            coordinates['high'].append(coordinate)
        elif days >= th_mid:
            coordinates['mid'].append(coordinate)
        elif days >= th_low:
            coordinates['low'].append(coordinate)
        else:
            coordinates['ok'].append(coordinate)
    
    bat_colors = (RED, ORANGE, YELLOW, GREEN)
    bat_labels = (f'> {th_high} days', f'> {th_mid} days', 
                  f'> {th_low} days', 'not exceeding')
    # note we assume keys are coming in order - check and maybe ordereddict
    for index, key in enumerate(coordinates):
        colors = [bat_colors[index] for _ in range(len(coordinates[key]))]
        if not colors:
            continue
        else:
            pass  # no points for this key
        
        geo_point = [Point(xy) for xy in coordinates[key]]
        gdf = GeoDataFrame(crs=EPSG_31256_adapted, geometry=geo_point)
        gdf = gdf.to_crs(epsg=EPSG_basemap)
        gdf.plot(ax=ax, alpha=0.4, c=colors, markersize=MARKERSIZE, 
                 label=bat_labels[index])

    swath_boundary = GeoSeries(swaths_geo_polygon, crs=EPSG_31256_adapted)
    swath_boundary = swath_boundary.to_crs(epsg=EPSG_basemap)
    swath_boundary.plot(ax=ax, alpha=0.2, color='red')
    
    if input('add basemap: [y/n]: ') in ['y', 'Y', 'yes', 'Yes', 'YES']:
        add_basemap(ax, zoom=13)

    ax.set_title(f'Bat status - {_date.strftime("%d %b")}', fontsize=20)
    plt.legend()    
    plt.show()

if __name__ == "__main__":
    nl = '\n'
    logger.info(f'{nl}=================================='\
                f'{nl}===>   Running: bat_plot.py   <==='\
                f'{nl}==================================')

    gd = GeoData()
    _date, swaths, geo_df, _, swaths_geo_polygon = gd.select_geo_data()

    plot_bat_status(geo_df, swaths_geo_polygon)
