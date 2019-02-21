import contextily as ctx
from pss_read import read_pss_for_date_range
from Utils.plogger import Logger
import numpy as np
import geopandas as gpd
from geopandas import GeoDataFrame, GeoSeries
from shapely.geometry import Point, Polygon
import matplotlib.pyplot as plt
from geo_io import GeoData, get_date_range, offset_transformation


PREFIX = r'plots\pss_plot_'
MARKERSIZE = 1
EPSG_31256_adapted = "+proj=tmerc +lat_0=0 +lon_0=16.33333333333333"\
                     " +k=1 +x_0=+500000 +y_0=0 +ellps=bessel "\
                     "+towgs84=577.326,90.129,463.919,5.137,1.474,5.297,2.4232 +units=m +no_defs"
EPSG_basemap = 3857 
EPSG_WGS84 = 4326
ZOOM = 13
HIGH=60
MEDIUM=35
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
        self.patch = []

        self.fig, self.ax = self.setup_map(figsize=(10, 10))
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
        _, _, _, swaths_bnd_gdf = GeoData().filter_geo_data_by_swaths(swaths_selected=self.swaths_selected, swaths_only=True)
        swaths_bnd_gdf.crs = EPSG_31256_adapted
        swaths_bnd_gdf = swaths_bnd_gdf.to_crs(epsg=EPSG_basemap)
        swaths_bnd_gdf.plot(ax=ax, facecolor='none', edgecolor='black')

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

        for ftype, data in vib_pss_gpd.groupby('force_level'):
            data.plot(ax=self.ax,
                      color=force_attrs[ftype][0],
                      label=force_attrs[ftype][1],
                      markersize=MARKERSIZE,)

    def on_click(self, event):
        print(f'event: {event}')
        self.update()

    def update(self):
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
    


    
