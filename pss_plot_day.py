import contextily as ctx
from pss_io import pss_group_force
from Utils.plogger import Logger, timed
import numpy as np
import geopandas as gpd
from pyproj import Proj, transform
from geopandas import GeoSeries
from shapely.geometry import Polygon
import matplotlib.pyplot as plt
from geo_io import GeoData, get_date, offset_transformation, swath_selection
from datetime import timedelta


PREFIX = r'plots\pss_plot_'
MARKERSIZE = 1
EDGECOLOR = 'black'
EPSG_31256_adapted = "+proj=tmerc +lat_0=0 +lon_0=16.33333333333333"\
                     " +k=1 +x_0=+500000 +y_0=0 +ellps=bessel "\
                     "+towgs84=577.326,90.129,463.919,5.137,1.474,5.297,2.4232 +units=m +no_defs"

EPSG_basemap = 3857 
proj_map = Proj(init=f'epsg:{EPSG_basemap}')
proj_local = Proj(EPSG_31256_adapted)

ZOOM = 13
HIGH_FORCE=60
MEDIUM_FORCE=35
OFFSET_INLINE = 6000.0
OFFSET_CROSSLINE = 6000.
maptitle = ('VPs 3D Schonkirchen', 18)
logger = Logger.getlogger()
nl = '\n'

class PlotMap:
    '''  class contains method to plot the pss data, swath boundary, map and 
         active patch
    '''
    def __init__(self, start_date, swaths_selected=[]):
        self.date = start_date
        self.swaths_selected = swaths_selected
        self.pss_dataframes = [None, None, None]
        self.init_pss_dataframes()

        self.fig, self.ax = self.setup_map(figsize=(5, 5))

        connect = self.fig.canvas.mpl_connect
        connect('button_press_event', self.on_click)
        connect('key_press_event', self.on_key)
        self.draw_cid = connect('draw_patch', self.grab_background)
        self.background = self.fig.canvas.copy_from_bbox(self.fig.bbox)

        # self.x, self.y = 1820000, 6150000
        self.date_text_x, self.date_text_y = 0.80, 0.95
        self.plot_pss_data(1)

    def setup_map(self, figsize):
        ''' setup the map and background '''
        fig, ax = plt.subplots(figsize=figsize)

        # plot the swath boundary
        _, _, _, swaths_bnd_gpd = GeoData().filter_geo_data_by_swaths(swaths_selected=self.swaths_selected, 
                                                                      swaths_only=True,
                                                                      source_boundary=True,)
        swaths_bnd_gpd.crs = EPSG_31256_adapted 
        swaths_bnd_gpd = swaths_bnd_gpd.to_crs(epsg=EPSG_basemap)
        swaths_bnd_gpd.plot(ax=ax, facecolor='none', edgecolor=EDGECOLOR)

        # obtain the extent of the data based on swaths_bnd_gdf
        extent_map = ax.axis()
        logger.info(f'extent data swaths: {extent_map}')

        # plot the basemap background
        url = 'http://tile.stamen.com/terrain/tileZ/tileX/tileY.png'
        plot_area = (extent_map[0], extent_map[2], extent_map[1], extent_map[3])
        logger.info(f'url: {url}, plot_area: {plot_area}')
        basemap, extent = ctx.bounds2img(*plot_area, zoom=ZOOM, url=url)
        ax.imshow(basemap, extent=extent, interpolation='bilinear')

        # restore original x/y limits
        ax.axis(extent_map)

        return fig, ax

    # @timed(logger)  #pylint: disable=no-value-for-parameter
    def init_pss_dataframes(self):
        dates = [self.date - timedelta(1), self.date, self.date + timedelta(1)]
        for i, _date in enumerate(dates):
            _pss_gpd = pss_group_force(_date, _date, HIGH_FORCE, MEDIUM_FORCE)
            _pss_gpd = _pss_gpd.to_crs(epsg=EPSG_basemap)
            self.pss_dataframes[i] = _pss_gpd

    # @timed(logger) #pylint: disable=no-value-for-parameter
    def update_right_pss_dataframes(self):
        self.pss_dataframes[0] = self.pss_dataframes[1]
        self.pss_dataframes[1] = self.pss_dataframes[2]
        _date = self.date+timedelta(1)
        _pss_gpd = pss_group_force(_date, _date, HIGH_FORCE, MEDIUM_FORCE)
        _pss_gpd = _pss_gpd.to_crs(epsg=EPSG_basemap)
        self.pss_dataframes[2] = _pss_gpd

    # @timed(logger) #pylint: disable=no-value-for-parameter
    def update_left_pss_dataframes(self):
        self.pss_dataframes[2] = self.pss_dataframes[1]
        self.pss_dataframes[1] = self.pss_dataframes[0]
        _date = self.date-timedelta(1)
        _pss_gpd = pss_group_force(_date, _date, HIGH_FORCE, MEDIUM_FORCE)
        _pss_gpd = _pss_gpd.to_crs(epsg=EPSG_basemap)
        self.pss_dataframes[0] = _pss_gpd

    # @timed(logger) #pylint: disable=no-value-for-parameter
    def plot_pss_data(self, index):
        '''  plot pss force data in three ranges LOW, MEDIUM, HIGH '''

        vib_pss_gpd = self.pss_dataframes[index]

        self.date_gid = plt.text(self.date_text_x, self.date_text_y, self.date.strftime("%d %m %y"),
                                 transform=self.ax.transAxes)
        if vib_pss_gpd.empty:
            self.blit()
            return False

        # plot the VP grouped by force_level
        force_attrs = { '1HIGH': ['red', f'high > {HIGH_FORCE}'],
                        '2MEDIUM': ['cyan', f'medium > {MEDIUM_FORCE}'],
                        '3LOW': ['yellow', f'low <= {MEDIUM_FORCE}'],}

        for force_level,vib_pss in vib_pss_gpd.groupby('force_level'):
            vib_pss.plot(ax=self.ax,
                         color=force_attrs[force_level][0],
                         label=force_attrs[force_level][1],
                         markersize=MARKERSIZE, gid='pss')

        self.blit()
        return True

    def on_click(self, event):
        # If we're using a tool on the toolbar, don't add/draw a point...
        if self.fig.canvas.toolbar._active is not None:
            return

        if event.button == 1:
            self.add_patch(event.xdata, event.ydata)
        elif event.button == 3:
            self.delete_from_map('patch')
            self.blit()

    # @timed(logger) #pylint: disable=no-value-for-parameter
    def on_key(self, event):
        if event.key not in ['right', 'left']:
            return

        self.delete_from_map('pss')
        if event.key == 'right':
            self.date += timedelta(1)
            self.plot_pss_data(2)
            logger.info('-------------------------------------------------------------------------')
            self.update_right_pss_dataframes()

        elif event.key == 'left':
            self.date -= timedelta(1)
            self.plot_pss_data(0)
            logger.info('-------------------------------------------------------------------------')
            self.update_left_pss_dataframes()


    def add_patch(self, x_map, y_map):
        # convert map point to local coordinate
        x, y = transform(proj_map, proj_local, x_map, y_map)

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
        patch_gpd = patch_gpd.to_crs(epsg=EPSG_basemap)
        patch_gpd.plot(ax=self.ax, facecolor='', edgecolor='red', gid='patch')

    def delete_from_map(self, gid):
        for plot_object in reversed(self.ax.collections):
            if plot_object.get_gid() == gid:
                plot_object.remove()

        try:
            self.date_gid.remove()
        except ValueError:
            pass

        # self.blit()

    def safe_draw(self):
        ''' temporary discinnect the draw event callback to avoid recursion error '''
        canvas = self.fig.canvas
        canvas.mpl_disconnect(self.draw_cid)
        canvas.draw()
        self.draw_cid = self.fig.canvas.mpl_connect('draw_event', self.grab_background)

    def grab_background(self, event=None):
        self.safe_draw()
        self.background = self.fig.canvas.copy_from_bbox(self.fig.bbox)
        self.blit()

    # @timed(logger) #pylint: disable=no-value-for-parameter
    def blit(self):
        
        self.fig.canvas.restore_region(self.background)
        plt.draw()
        self.fig.canvas.blit(self.fig.bbox)

    def show(self):
        plt.show()

def main():
    start_date = get_date()
    PlotMap(start_date).show()

if __name__ == "__main__":
    logger.info(f'{nl}==============================================='\
                f'{nl}===>   Running: pss_plot_day (optimized)   <==='\
                f'{nl}===============================================')

    main()
    