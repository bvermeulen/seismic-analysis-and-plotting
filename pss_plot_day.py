import sys
from datetime import timedelta
import matplotlib.pyplot as plt

import set_gdal_pyproj_env_vars_and_logger  #pylint: disable=W0611
from geopandas import GeoSeries  #pylint: disable=C0411
from shapely.geometry import Polygon  #pylint: disable=C0411
from pyproj import Proj, transform  #pylint: disable=C0411

from pss_io import get_vps_force_for_date_range
from geo_io import (GeoData, get_date, offset_transformation,
                    add_basemap_local, add_basemap_osm,
                    EPSG_31256_adapted, EPSG_OSM)
from Utils.plogger import Logger, timed


MARKERSIZE = 0.02
EDGECOLOR = 'black'
maptypes = ['local', 'osm']

proj_map = Proj(init=f'epsg:{EPSG_OSM}')
proj_local = Proj(EPSG_31256_adapted)

ZOOM = 13
HIGH_FORCE = 60
MEDIUM_FORCE = 35
OFFSET_INLINE = 6000.0
OFFSET_CROSSLINE = 6000.0
maptitle = ('VPs 3D Schonkirchen', 18)
logger = Logger.getlogger()
nl = '\n'

class PlotMap:
    '''  class contains method to plot the pss data, swath boundary, map and
         active patch
    '''
    def __init__(self, start_date, maptype=None, swaths_selected=[]):
        self.date = start_date
        self.maptype = maptype
        self.swaths_selected = swaths_selected
        self.pss_dataframes = [None, None, None]
        self.init_pss_dataframes()

        self.fig, self.ax = self.setup_map(figsize=(5, 5))
        self.background = self.fig.canvas.copy_from_bbox(self.fig.bbox)

        connect = self.fig.canvas.mpl_connect
        connect('button_press_event', self.on_click)
        connect('key_press_event', self.on_key)

        self.date_text_x, self.date_text_y = 0.80, 0.95
        self.plot_pss_data(1)

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

    # @timed(logger)  #pylint: disable=no-value-for-parameter
    def init_pss_dataframes(self):
        dates = [self.date - timedelta(1), self.date, self.date + timedelta(1)]
        for i, _date in enumerate(dates):
            _pss_gpd = get_vps_force_for_date_range(_date, _date,
                                                    MEDIUM_FORCE, HIGH_FORCE)
            _pss_gpd = self.convert_to_map(_pss_gpd)
            self.pss_dataframes[i] = _pss_gpd

    # @timed(logger) #pylint: disable=no-value-for-parameter
    def update_right_pss_dataframes(self):
        self.pss_dataframes[0] = self.pss_dataframes[1]
        self.pss_dataframes[1] = self.pss_dataframes[2]
        _date = self.date+timedelta(1)
        _pss_gpd = get_vps_force_for_date_range(_date, _date, MEDIUM_FORCE, HIGH_FORCE)
        _pss_gpd = self.convert_to_map(_pss_gpd)
        self.pss_dataframes[2] = _pss_gpd

    # @timed(logger) #pylint: disable=no-value-for-parameter
    def update_left_pss_dataframes(self):
        self.pss_dataframes[2] = self.pss_dataframes[1]
        self.pss_dataframes[1] = self.pss_dataframes[0]
        _date = self.date-timedelta(1)
        _pss_gpd = get_vps_force_for_date_range(_date, _date, MEDIUM_FORCE, HIGH_FORCE)
        _pss_gpd = self.convert_to_map(_pss_gpd)
        self.pss_dataframes[0] = _pss_gpd

    # @timed(logger) #pylint: disable=no-value-for-parameter
    def plot_pss_data(self, index):
        '''  plot pss force data in three ranges LOW, MEDIUM, HIGH '''

        vib_pss_gpd = self.pss_dataframes[index]

        self.date_gid = plt.text(self.date_text_x, self.date_text_y,
                                 self.date.strftime("%d %m %y"),
                                 transform=self.ax.transAxes)
        if vib_pss_gpd.empty:
            self.blit()
            return False

        # plot the VP grouped by force_level
        force_attrs = {'1HIGH': ['red', f'high > {HIGH_FORCE}'],
                       '2MEDIUM': ['cyan', f'medium > {MEDIUM_FORCE}'],
                       '3LOW': ['yellow', f'low <= {MEDIUM_FORCE}'],}

        for force_level, vib_pss in vib_pss_gpd.groupby('force_level'):
            vib_pss.plot(ax=self.ax,
                         color=force_attrs[force_level][0],
                         markersize=MARKERSIZE, gid='pss')

        self.blit()
        return True

    def on_click(self, event):
        # If we're using a tool on the toolbar, don't add/draw a point...
        if self.fig.canvas.toolbar._active is not None:  #pylint: disable=W0212
            return

        if event.button == 1:
            self.add_patch(event.xdata, event.ydata)
        elif event.button == 3:
            self.delete_from_map('patch')
            self.blit()

    @timed(logger) #pylint: disable=no-value-for-parameter
    def on_key(self, event):
        if event.key not in ['right', 'left']:
            return

        logger.info(f'|------------------------| {event.key} |------------------------|')
        self.delete_from_map('pss')
        if event.key == 'right':
            self.date += timedelta(1)
            self.plot_pss_data(2)
            self.update_right_pss_dataframes()

        elif event.key == 'left':
            self.date -= timedelta(1)
            self.plot_pss_data(0)
            self.update_left_pss_dataframes()

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

        if gid == 'pss':
            try:
                self.date_gid.remove()
            except ValueError:
                pass

    def convert_to_map(self, df):
        if self.maptype == maptypes[1] and not df.empty:
            df = df.to_crs(epsg=EPSG_OSM)
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


def main(maptype):
    start_date = get_date()
    PlotMap(start_date, maptype=maptype).show()

if __name__ == "__main__":
    '''  Interactive display of production. Background maps can be
         selected by giving an argument.
         :arguments:
            local: local map (jpg) - very slow
            OSM: OpenStreetMap - slow
            No arguments or anything else: no background map
    '''

    logger.info(f'{nl}==============================================='\
                f'{nl}===>   Running: pss_plot_day (optimized)   <==='\
                f'{nl}===============================================')

    try:
        maptype = sys.argv[1].lower()
        if maptype not in maptypes:
            maptype = None
    except IndexError:
        maptype = None

    logger.info(f'maptype: {maptype}')
    main(maptype)
