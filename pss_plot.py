import contextily as ctx
from pss_read import read_pss_for_date_range
from Utils.plogger import Logger
import numpy as np
import geopandas as gpd
from geopandas import GeoDataFrame
from shapely.geometry import Point
import matplotlib.pyplot as plt

MARKERSIZE = 3

def add_basemap(ax, zoom, url='http://tile.stamen.com/terrain/tileZ/tileX/tileY.png'):
    logger = Logger.getlogger()
    xmin, xmax, ymin, ymax = ax.axis()
    logger.info(f'url: {url}')
    basemap, extent = ctx.bounds2img(xmin, ymin, xmax, ymax, zoom=zoom, url=url)
    ax.imshow(basemap, extent=extent, interpolation='bilinear')
    # restore original x/y limits
    ax.axis((xmin, xmax, ymin, ymax))


def pss_plot_function():
    logger = Logger.getlogger()
    vp_longs, vp_lats, vp_colors = read_pss_for_date_range()
    vib_points_df = [Point(xy) for xy in zip(vp_longs, vp_lats)]
    crs = {'init':'epsg:4326'}
    gdf = GeoDataFrame(crs=crs, geometry=vib_points_df)
    gdf = gdf.to_crs(epsg=3857)

    # gdf.head()
    ax = gdf.plot(figsize=(10, 10), alpha=0.5, c=vp_colors, markersize=MARKERSIZE)
    zoom = 13
    reduce = True
    while reduce:
        try:
            add_basemap(ax, zoom=zoom)
            reduce = False
            logger.info(f'zoom factor: {zoom}')
        except:
            zoom -= 1
        
    plt.show()


if __name__ == "__main__":
    logformat = '%(asctime)s - %(levelname)s - %(message)s'
    Logger.set_logger('pss_plot.log', logformat, 'DEBUG')
    pss_plot_function()
