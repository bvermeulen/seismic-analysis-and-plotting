from pss_read import read_pss_for_date_range
from Utils.plogger import Logger
import numpy as np
import geopandas as gpd
from geopandas import GeoDataFrame, GeoSeries
from shapely.geometry import Point
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap 
from PIL import Image
from geo_io import swath_selection


MAP_FILE = r'BackgroundMap/3D_31256.jpg'
EPSG_31256_adapted = "+proj=tmerc +lat_0=0 +lon_0=16.33333333333333"\
                     " +k=1 +x_0=+500000 +y_0=0 +ellps=bessel "\
                     "+towgs84=577.326,90.129,463.919,5.137,1.474,5.297,2.4232 +units=m +no_defs"
EPSG_basemap = 3857 
EPSG_WGS84 = 4326

Image.MAX_IMAGE_PIXELS = 2000000000
MARKERSIZE = 5
HIGH=65
MEDIUM=45
maptitle = ('VPs 3D Schonkirchen', 20)
logger = Logger.getlogger()


def group_forces(forces, high, medium):
    grouped_forces = []
    for force in forces:
        if force > high:
            grouped_forces.append('1HIGH')
        elif force > medium:
            grouped_forces.append('2MEDIUM')
        elif force <= medium:
            grouped_forces.append('3LOW')
        else:
            assert False, "this is an invalid option, check the code"
    
    return grouped_forces

def add_basemap(ax):
    '''  load the map in picture format and the georeference information from the jgW file 
         in the same folder; the crs has to be the same as the data 

         :input: ax 
         :output: none  
    '''
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


def pss_plot_function():
    _, ax = plt.subplots(figsize=(10, 10))    

    vp_longs, vp_lats, vp_forces = read_pss_for_date_range()
    vib_points_df = [Point(xy) for xy in zip(vp_longs, vp_lats)]
    crs = {'init': f'epsg:{EPSG_WGS84}'}
    gdf = GeoDataFrame(crs=crs, geometry=vib_points_df)
    gdf = gdf.to_crs(crs=EPSG_31256_adapted)
    vp_forces = group_forces(vp_forces, HIGH, MEDIUM)
    gdf['forces'] = vp_forces
    force_attrs = { '1HIGH': ['red', f'high > {HIGH}'],
                    '2MEDIUM': ['cyan', f'medium > {MEDIUM}'],
                    '3LOW': ['yellow', f'low <= {MEDIUM}'],}
    
    for ftype, data in gdf.groupby('forces'):
        data.plot(ax=ax,
                  color=force_attrs[ftype][0],
                  label=force_attrs[ftype][1],
                  markersize=MARKERSIZE,)

    nl = '\n'; logger.info(f'geometry header: {nl}{gdf.head()}')

    swath_polygons = swath_selection()
    swath_boundary = GeoSeries(swath_polygons, crs=EPSG_31256_adapted)
    swath_boundary.plot(ax=ax, alpha=0.2, color='red')

    add_basemap(ax)
    ax.legend(title='Legend')
    ax.set_title(maptitle[0], fontsize=maptitle[1])
    plt.show()


if __name__ == "__main__":
    nl = '\n'
    logger.info(f'{nl}======================================'\
                f'{nl}===>   Running: pss_plot_jpg.py   <==='\
                f'{nl}======================================')

    pss_plot_function()
