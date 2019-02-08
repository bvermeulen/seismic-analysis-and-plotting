import contextily as ctx
from pss_read import read_pss_for_date_range
from Utils.plogger import Logger
import numpy as np
import geopandas as gpd
from geopandas import GeoDataFrame, GeoSeries
from shapely.geometry import Point
import matplotlib.pyplot as plt
from geo_io import GeoData


MARKERSIZE = 3
EPSG_31256_adapted = "+proj=tmerc +lat_0=0 +lon_0=16.33333333333333"\
                     " +k=1 +x_0=+500000 +y_0=0 +ellps=bessel "\
                     "+towgs84=577.326,90.129,463.919,5.137,1.474,5.297,2.4232 +units=m +no_defs"
EPSG_basemap = 3857 
EPSG_WGS84 = 4326
ZOOM = 13
HIGH=60
MEDIUM=35
maptitle = ('VPs 3D Schonkirchen', 20)
logger = Logger.getlogger()
nl = '\n'

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


def add_basemap(ax, plot_area, zoom, url='http://tile.stamen.com/terrain/tileZ/tileX/tileY.png'):
    logger.info(f'url: {url}')
    basemap, extent = ctx.bounds2img(*plot_area, zoom=zoom, url=url)
    ax.imshow(basemap, extent=extent, interpolation='bilinear')


def pss_plot_function():
    _, ax = plt.subplots(figsize=(10, 10))    

    vp_longs, vp_lats, vp_forces = read_pss_for_date_range()
    vib_points_df = [Point(xy) for xy in zip(vp_longs, vp_lats)]
    crs = {'init': f'epsg:{EPSG_WGS84}'}
    gdf = GeoDataFrame(crs=crs, geometry=vib_points_df)
    gdf = gdf.to_crs(epsg=EPSG_basemap)
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

    logger.info(f'geometry header: {nl}{gdf.head()}')

    gd = GeoData()
    _, _, _, swaths_bnd_gdf = gd.filter_geo_data_by_swaths(swaths_only=True)
    swaths_bnd_gdf.crs = EPSG_31256_adapted
    swaths_bnd_gdf = swaths_bnd_gdf.to_crs(epsg=EPSG_basemap)
    swaths_bnd_gdf.plot(ax=ax, facecolor='none', edgecolor='black')

    # obtain the extent of the data based on swaths_bnd_gdf
    extent_data = ax.axis()
    logger.info(f'extent data: {extent_data}')

    add_basemap(ax, (extent_data[0], extent_data[2], extent_data[1], extent_data[3]), zoom=ZOOM)
    logger.info(f'zoom factor: {ZOOM}')

    # restore original x/y limits
    ax.axis(extent_data)
    ax.legend(title='Legend')
    ax.set_title(maptitle[0], fontsize=maptitle[1])
    plt.show()


if __name__ == "__main__":
    logger.info(f'{nl}=================================='\
                f'{nl}===>   Running: pss_plot.py   <==='\
                f'{nl}==================================')


    pss_plot_function()
