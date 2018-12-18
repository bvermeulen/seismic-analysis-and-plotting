from pss_read import read_pss_for_date_range
from Utils.plogger import Logger
import numpy as np
import geopandas as gpd
from geopandas import GeoDataFrame
from shapely.geometry import Point
import matplotlib.pyplot as plt
from PIL import Image


# EPSG = 4326 # WGS84
# MAP_FILE = r'BackgroundMap/3D_OMV_SKN2_DNS_Topo1800dpi_transformed.jpg'

EPSG_31256_adapted = "+proj=tmerc +lat_0=0 +lon_0=16.33333333333333"\
                     " +k=1 +x_0=+500000 +y_0=0 +ellps=bessel "\
                     "+towgs84=577.326,90.129,463.919,5.137,1.474,5.297,2.4232 +units=m +no_defs"
MAP_FILE = r'BackgroundMap/3D_31256.jpg'

# EPSG = 32633 # UTM Zone 33 N  
# MAP_FILE = r'BackgroundMap/OMV_3D_33N_2'

Image.MAX_IMAGE_PIXELS = 2000000000
MARKERSIZE = 2


def add_basemap(ax):
    '''  load the map in picture format and the georeference information from the jgW file 
         in the same folder; the crs has to be the same as the data 

         :input: ax 
         :output: none  
    '''
    logger = Logger.getlogger()

    # obtain the extent of the data to restore later
    extent_data = ax.axis()
    logger.info(f'extent data: {extent_data}')

    # read the map image file and set the extent
    fname_jgW = MAP_FILE[:-4] + '.jgW' 
    basemap = plt.imread(MAP_FILE)
    cols = basemap.shape[0]
    rows = basemap.shape[1]

    with open(fname_jgW, 'tr') as jgw:
        dx = float(jgw.readline())
        _ = jgw.readline()  # to do with rotation of the map to be ignored
        _ = jgw.readline()  # to do with rotation of the map to be ignored
        dy = float(jgw.readline())
        x_min = float(jgw.readline())
        y_max = float(jgw.readline())
    
    x_max = x_min + rows * dx
    y_min = y_max + cols * dy
    logger.info(f'filename: {MAP_FILE}, (rows: {rows}, colums: {cols}), \n'\
                f'extent map crs:{EPSG_31256_adapted}: \n {(x_min, x_max, y_min, y_max)}')

    ax.imshow(basemap, extent=(x_min, x_max, y_min, y_max), interpolation='bilinear')

    # restore original x/y limits
    ax.axis(extent_data)


def add_map_title(ax):
    ax.set_title('VPs 3D Schonkirchen')


def pss_plot_function():
    logger = Logger.getlogger()
    vp_longs, vp_lats, vp_colors = read_pss_for_date_range()
    vib_points_df = [Point(xy) for xy in zip(vp_longs, vp_lats)]
    crs = {'init':'epsg:4326'}
    gdf = GeoDataFrame(crs=crs, geometry=vib_points_df)
    gdf = gdf.to_crs(EPSG_31256_adapted)

    logger.info(f'geometry header: {gdf.head()}')
    ax = gdf.plot(figsize=(10, 10), alpha=0.5, c=vp_colors, markersize=MARKERSIZE)
    add_basemap(ax)
    # add_map_title(ax)    
    plt.show()


if __name__ == "__main__":
    logformat = '%(asctime)s - %(levelname)s - %(message)s'
    Logger.set_logger('pss_plot_jpg.log', logformat, 'INFO')
    pss_plot_function()
