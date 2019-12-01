import sys
import matplotlib.pyplot as plt

import set_gdal_pyproj_env_vars_and_logger  #pylint: disable=W0611
from pyproj import Proj, transform  #pylint: disable=C0411
from geopandas import GeoSeries  #pylint: disable=C0411
from shapely.geometry import Polygon  #pylint: disable=C0411

from pss_attr import pss_attr
from pss_io import get_vps_attribute_for_date_range
from geo_io import (GeoData, get_date_range, offset_transformation,
                    add_basemap_local, add_basemap_osm,
                    EPSG_31256_adapted, EPSG_OSM)
from Utils.plogger import Logger, timed


MARKERSIZE = 0.2
EDGECOLOR = 'black'
maptypes = ['local', 'osm']
cmap = 'coolwarm'

proj_map = Proj(init=f'epsg:{EPSG_OSM}')
proj_local = Proj(EPSG_31256_adapted)

ZOOM = 13
OFFSET_INLINE = 6000.0
OFFSET_CROSSLINE = 6000.0
maptitle = ('VPs 3D Schonkirchen', 18)
logger = Logger.getlogger()
nl = '\n'

class PlotMap:
    '''  class contains method to plot the pss data, swath boundary, map and
         active patch
    '''
    def __init__(self, maptype=None, swaths_selected=None):
        self.maptype = maptype
        self.swaths_selected = swaths_selected

        self.fig, self.ax = self.setup_map(figsize=(6, 5))
        self.background = self.fig.canvas.copy_from_bbox(self.fig.bbox)

        connect = self.fig.canvas.mpl_connect
        connect('button_press_event', self.on_click)

    def setup_map(self, figsize):
        ''' setup the map and background '''
        fig, ax = plt.subplots(figsize=figsize)

        # plot the swath boundary
        _, _, _, swaths_bnd_gpd = GeoData().filter_geo_data_by_swaths(
            swaths_selected=self.swaths_selected,
            swaths_only=True,
            source_boundary=True,)
        swaths_bnd_gpd = self.convert_to_map(swaths_bnd_gpd)
        swaths_bnd_gpd.plot(ax=ax, facecolor='none', edgecolor=EDGECOLOR)

        # obtain the extent of the data based on swaths_bnd_gdf
        extent_map = ax.axis()
        logger.info(f'extent data swaths: {extent_map}')

        # plot the selected basemap background
        plot_area = (extent_map[0], extent_map[2], extent_map[1], extent_map[3])
        if self.maptype == maptypes[0]:
            add_basemap_local(ax)
        elif self.maptype == maptypes[1]:
            add_basemap_osm(ax, plot_area, ZOOM)
        else:
            pass  # no basemap background

        # restore original x/y limits
        ax.axis(extent_map)

        return fig, ax

    # @timed(logger) #pylint: disable=no-value-for-parameter
    def plot_attribute_data(self, attribute, start_date, end_date):
        '''  plot vp attribute data '''

        vib_attribute_gpd = get_vps_attribute_for_date_range(
            attribute, start_date, end_date)
        vib_attribute_gpd = self.convert_to_map(vib_attribute_gpd)

        if vib_attribute_gpd.empty:
            self.blit()
            return False

        # determine minumum and maximum
        if pss_attr[attribute]['min'] is not None:
            minimum = pss_attr[attribute]['min']
        else:
            minimum = vib_attribute_gpd[attribute].min()

        if pss_attr[attribute]['max'] is not None:
            maximum = pss_attr[attribute]['max']
        else:
            maximum = vib_attribute_gpd[attribute].max()
        logger.info(f'minimum: {minimum}, maximum: {maximum}')

        vib_attribute_gpd.plot(ax=self.ax,
                               column=attribute,
                               cmap=cmap,
                               vmin=minimum, vmax=maximum,
                               markersize=MARKERSIZE, gid='pss')

        self.add_colorbar(cmap, minimum, maximum)
        self.ax.set_title(' '.join(['Schonkirchen 3D:', pss_attr[attribute]['title']]))

        self.blit()

    def add_colorbar(self, cmap, minimum, maximum):
        ''' plot the colorbar
            https://stackoverflow.com/questions/36008648/colorbar-on-geopandas
        '''
        cax = self.fig.add_axes([0.9, 0.1, 0.03, 0.8])
        sm = plt.cm.ScalarMappable(cmap=cmap,
                                   norm=plt.Normalize(vmin=minimum, vmax=maximum))
        sm._A = []  #pylint: disable=protected-access
        self.fig.colorbar(sm, cax=cax)

    def on_click(self, event):
        # If we're using a tool on the toolbar, don't add/draw a point...
        if self.fig.canvas.toolbar._active is not None:  #pylint: disable=protected-access
            return

        if event.button == 1:
            self.add_patch(event.xdata, event.ydata)
        elif event.button == 3:
            self.delete_from_map('patch')
            self.blit()

    def add_patch(self, x_map, y_map):
        # convert map point to local coordinate
        if self.maptype == maptypes[1]:
            x, y = transform(proj_map, proj_local, x_map, y_map)
        else:
            x, y = x_map, y_map

        c1 = tuple([x + offset_transformation(OFFSET_INLINE, OFFSET_CROSSLINE)[0],
                    y + offset_transformation(OFFSET_INLINE, OFFSET_CROSSLINE)[1]])
        c2 = tuple([x + offset_transformation(OFFSET_INLINE, -OFFSET_CROSSLINE)[0],
                    y + offset_transformation(OFFSET_INLINE, -OFFSET_CROSSLINE)[1]])
        c3 = tuple([x + offset_transformation(-OFFSET_INLINE, -OFFSET_CROSSLINE)[0],
                    y + offset_transformation(-OFFSET_INLINE, -OFFSET_CROSSLINE)[1]])
        c4 = tuple([x + offset_transformation(-OFFSET_INLINE, OFFSET_CROSSLINE)[0],
                    y + offset_transformation(-OFFSET_INLINE, OFFSET_CROSSLINE)[1]])

        # set corner points of patch and convert back to map coordinates
        patch_polygon = Polygon([c1, c2, c3, c4, c1])
        patch_gpd = GeoSeries(patch_polygon)
        patch_gpd.crs = EPSG_31256_adapted
        patch_gpd = self.convert_to_map(patch_gpd)
        patch_gpd.plot(ax=self.ax, facecolor='', edgecolor='red', gid='patch')

    def delete_from_map(self, gid):
        for plot_object in reversed(self.ax.collections):
            if plot_object.get_gid() == gid:
                plot_object.remove()

    def convert_to_map(self, df):
        if self.maptype == maptypes[1] and not df.empty:
            df = df.to_crs(f'epsg:{EPSG_OSM}')
        else:
            pass
        return df

    @timed(logger) #pylint: disable=no-value-for-parameter
    def blit(self):
        self.fig.canvas.restore_region(self.background)
        plt.draw()
        self.fig.canvas.blit(self.fig.bbox)

    def show(self):
        plt.show()


def main(maptype, attribute):
    start_date, end_date = get_date_range()
    plotmap = PlotMap(maptype=maptype)
    plotmap.plot_attribute_data(attribute, start_date, end_date)
    plotmap.show()

if __name__ == "__main__":
    '''  Interactive display of production. Background maps can be
         selected by giving an argument.
         :arguments:
            first argument:
                local: local map (jpg) - very slow
                OSM: OpenStreetMap - slow
                none: no background map
            second argument:
                pss attribute as given in pss_attr.py (i.e. 'Force Avg' or 'Altitude')
                if none then 'Altitude' is taken
    '''

    logger.info(f'{nl}=========================================='\
                f'{nl}===>   Running: pss_plot_attribute    <==='\
                f'{nl}==========================================')

    try:
        maptype = sys.argv[1].lower()
        if maptype not in maptypes:
            maptype = None
    except IndexError:
        maptype = None

    try:
        attribute = sys.argv[2]
        if attribute not in pss_attr:
            print('provide valid attribute as second argument')
            sys.exit()
    except IndexError:
        attribute = 'Altitude'

    logger.info(f'maptype: {maptype}, attribute: {attribute}')
    main(maptype, attribute)
