import contextily as ctx
from pss_read import read_pss_for_date_range
from Utils.plogger import Logger
import numpy as np
import geopandas as gpd
from pyproj import Proj, transform
from geopandas import GeoDataFrame, GeoSeries
from shapely.geometry import Point, Polygon
import matplotlib.pyplot as plt
from geo_io import GeoData, get_date_range, offset_transformation, swath_selection, make_square, df_to_excel
import pdb


PREFIX = r'plots\pss_plot_'
MARKERSIZE = 1
EDGECOLOR = 'black'
EPSG_31256_adapted = "+proj=tmerc +lat_0=0 +lon_0=16.33333333333333"\
                     " +k=1 +x_0=+500000 +y_0=0 +ellps=bessel "\
                     "+towgs84=577.326,90.129,463.919,5.137,1.474,5.297,2.4232 +units=m +no_defs"
EPSG_basemap = 3857 
EPSG_WGS84 = 4326
proj_map = Proj(init=f'epsg:{EPSG_basemap}')
proj_local = Proj(EPSG_31256_adapted)

ZOOM = 13
HIGH=60
MEDIUM=35
OFFSET_INLINE = 6000.0
OFFSET_CROSSLINE = 3000.
maptitle = ('VPs 3D Schonkirchen', 18)
logger = Logger.getlogger()
nl = '\n'

class PlotMap:
    '''  class contains method to plot the pss data, swath boundary, map and 
         active patch
    '''
    def __init__(self, start_date, end_date, swaths_selected=[]):
        self.start_date = start_date
        self.end_date = end_date
        self.swaths_selected = swaths_selected

        self.fig, self.ax = self.setup_map(figsize=(5, 5))
        self.plot_pss_data()

        connect = self.fig.canvas.mpl_connect
        connect('button_press_event', self.on_click)
        self.draw_cid = connect('draw_patch', self.grab_background)
        self.background = self.fig.canvas.copy_from_bbox(self.fig.bbox)
        self.blit_counter = 0

    def setup_map(self, figsize):
        ''' setup the map and background '''
        fig, ax = plt.subplots(figsize=figsize)

        # plot the swath boundary
        _, _, _, swaths_bnd_gpd = GeoData().filter_geo_data_by_swaths(swaths_selected=self.swaths_selected, swaths_only=True)
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

    def plot_pss_data(self):
        '''  plot pss force data in three ranges LOW, MEDIUM, HIGH '''
        def group_forces(forces, high, medium):
            ''' helper function to group forces in LOW, MEDIUM , HIGH '''
            force_levels = []
            for force in forces:
                if force > high:
                    force_levels.append('1HIGH')
                elif force > medium:
                    force_levels.append('2MEDIUM')
                elif force <= medium:
                    force_levels.append('3LOW')
                else:
                    assert False, "this is an invalid option, check the code"
            return force_levels

        vp_longs, vp_lats, vp_forces = read_pss_for_date_range(self.start_date, self.end_date)
        vib_points_df = [Point(xy) for xy in zip(vp_longs, vp_lats)]
        crs = {'init': f'epsg:{EPSG_WGS84}'}
        vib_pss_gpd = GeoDataFrame(crs=crs, geometry=vib_points_df)
        vib_pss_gpd = vib_pss_gpd.to_crs(epsg=EPSG_basemap)
        vib_pss_gpd['force_level'] = group_forces(vp_forces, HIGH, MEDIUM)
        
        # plot the VP grouped by force_level
        force_attrs = { '1HIGH': ['red', f'high > {HIGH}'],
                        '2MEDIUM': ['cyan', f'medium > {MEDIUM}'],
                        '3LOW': ['yellow', f'low <= {MEDIUM}'],}

        for force_level,vib_pss in vib_pss_gpd.groupby('force_level'):
            vib_pss.plot(ax=self.ax,
                         color=force_attrs[force_level][0],
                         label=force_attrs[force_level][1],
                         markersize=MARKERSIZE,)

    def on_click(self, event):
        print(f'event: {event}')
        # If we're using a tool on the toolbar, don't add/draw a point...
        if self.fig.canvas.toolbar._active is not None:
            return

        if event.button == 1:
            self.add_patch(event.xdata, event.ydata)
        elif event.button == 3:
            self.delete_patch()

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

    def delete_patch(self):
        not_ready = True
        while not_ready: 
            for plot_object in self.ax.collections:
                if plot_object.get_gid() == 'patch':
                    plot_object.remove()
            not_ready = any([plot_object._gid == 'patch' for plot_object in self.ax.collections])
        self.blit()

    def safe_draw(self):
        ''' temporary discinnect the draw event callback to avoid recursion error '''
        canvas = self.fig.canvas
        canvas.mpl_disconnect(self.draw_cid)
        canvas.draw()
        self.draw_cid = self.fig.canvas.mpl_connect('draw_event', self.grab_background)

    def grab_background(self, event=None):
        print('in grab_background')
        self.safe_draw()
        self.background = self.fig.canvas.copy_from_bbox(self.fig.bbox)
        self.blit()

    def blit(self):
        self.blit_counter += 1
        print(f'in blit: {self.blit_counter}')
        
        self.fig.canvas.restore_region(self.background)
        plt.draw()
        self.fig.canvas.blit(self.fig.bbox)

    def show(self):
        plt.show()

def main():
    start_date, end_date = get_date_range()
    PlotMap(start_date, end_date).show()

if __name__ == "__main__":
    logger.info(f'{nl}=================================='\
                f'{nl}===>   Running: pss_plot.py   <==='\
                f'{nl}==================================')

    main()
    


    
