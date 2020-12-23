import sys
from datetime import timedelta
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle
import pyproj
from pss_io import get_vps_force_for_date_range
from geo_io import (
    GeoData, get_date, offset_transformation, add_basemap_local, add_basemap_osm,
    EPSG_31256_adapted, EPSG_OSM)
from Utils.plogger import Logger

#pylint: disable=no-value-for-parameter

MARKERSIZE = 0.04
EDGECOLOR = 'black'
maptypes = ['local', 'osm']

# transformations from map to local and vice versa
proj_map = pyproj.Proj(f'epsg:{EPSG_OSM}')
proj_local = pyproj.Proj(EPSG_31256_adapted)
t_map_local = pyproj.Transformer.from_proj(proj_map, proj_local)
t_local_map = pyproj.Transformer.from_proj(proj_local, proj_map)

FIGSIZE = (8, 8)
MEDIUM_FORCE = 35
HIGH_FORCE = 60
OFFSET_INLINE = 6000.0
OFFSET_CROSSLINE = 6000.0
SOURCE_CENTER = MARKERSIZE * 7500
SOURCE_COLOR = 'blue'
maptitle = ('VPs 3D Schonkirchen', 18)
force_attrs = {'1HIGH': ['red', f'high > {HIGH_FORCE}'],
               '2MEDIUM': ['cyan', f'medium > {MEDIUM_FORCE}'],
               '3LOW': ['yellow', f'low <= {MEDIUM_FORCE}'],}

logger = Logger.getlogger()
nl = '\n'

class PlotMap:
    '''  class contains method to plot the pss data, swath boundary, map and
         active receivers
    '''
    def __init__(self, start_date, maptype=None, swaths_selected=None):
        self.date = start_date
        self.maptype = maptype
        self.swaths_selected = swaths_selected
        self.pss_dataframes = [None, None, None]
        self.init_pss_dataframes()

        self.fig, self.ax = self.setup_map(figsize=FIGSIZE)

        connect = self.fig.canvas.mpl_connect
        connect('button_press_event', self.on_click)
        connect('key_press_event', self.on_key)
        connect('resize_event', self.on_resize)

        self.resize_timer = self.fig.canvas.new_timer(interval=250)
        self.resize_timer.add_callback(self.blit)

        # start event loop
        self.artists_on_stage = False
        self.background = None
        self.show(block=False)
        plt.pause(0.1)
        self.blit()

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
        if self.maptype == maptypes[0]:
            add_basemap_local(ax)

        elif self.maptype == maptypes[1]:
            add_basemap_osm(ax)

        else:
            pass  # no basemap background

        # restore original x/y limits
        ax.axis(extent_map)

        return fig, ax

    def setup_artists(self):
        date_text_x, date_text_y = 0.80, 0.95
        self.vib_artists = {}
        for force_level, force_attr in force_attrs.items():
            self.vib_artists[force_level] = self.ax.scatter(
                [0,], [0,], s=MARKERSIZE, marker='o', facecolor=force_attr[0],)
        self.date_artist = self.ax.text(
            date_text_x, date_text_y, '', transform=self.ax.transAxes,)
        self.actrecv_artist = Polygon(np.array(
            [[0, 0]]), closed=True, edgecolor='red', fill=False)
        self.ax.add_patch(self.actrecv_artist)
        self.cp_artist = Circle((0, 0), radius=SOURCE_CENTER, fc=SOURCE_COLOR)
        self.ax.add_patch(self.cp_artist)
        self.artists_on_stage = True

    def remove_artists(self):
        if self.artists_on_stage:
            for _, vib_artist in self.vib_artists.items():
                vib_artist.remove()
            self.date_artist.remove()
            self.actrecv_artist.remove()
            self.cp_artist.remove()
            self.artists_on_stage = False

        else:
            pass

    def init_pss_dataframes(self):
        dates = [self.date - timedelta(1), self.date, self.date + timedelta(1)]
        for i, _date in enumerate(dates):
            _pss_gpd = get_vps_force_for_date_range(
                _date, _date, MEDIUM_FORCE, HIGH_FORCE)
            _pss_gpd = self.convert_to_map(_pss_gpd)
            self.pss_dataframes[i] = _pss_gpd

    def update_right_pss_dataframes(self):
        self.pss_dataframes[0] = self.pss_dataframes[1]
        self.pss_dataframes[1] = self.pss_dataframes[2]
        _date = self.date+timedelta(1)
        _pss_gpd = get_vps_force_for_date_range(_date, _date, MEDIUM_FORCE, HIGH_FORCE)
        _pss_gpd = self.convert_to_map(_pss_gpd)
        self.pss_dataframes[2] = _pss_gpd

    def update_left_pss_dataframes(self):
        self.pss_dataframes[2] = self.pss_dataframes[1]
        self.pss_dataframes[1] = self.pss_dataframes[0]
        _date = self.date-timedelta(1)
        _pss_gpd = get_vps_force_for_date_range(_date, _date, MEDIUM_FORCE, HIGH_FORCE)
        _pss_gpd = self.convert_to_map(_pss_gpd)
        self.pss_dataframes[0] = _pss_gpd

    def plot_pss_data(self, index):
        '''  plot pss force data in three ranges LOW, MEDIUM, HIGH '''
        vib_pss_gpd = self.pss_dataframes[index]
        self.date_artist.set_text(self.date.strftime("%d %m %y"))

        # plot the VP grouped by force_level
        if not vib_pss_gpd.empty:
            for force_level, vib_pss in vib_pss_gpd.groupby('force_level'):
                if pts:=[(xy.x, xy.y) for xy in vib_pss['geometry'].to_list()]:
                    self.vib_artists[force_level].set_offsets(pts)

                else:
                    self.vib_artists[force_level].set_offsets([[0, 0]])

        else:
            for force_level in force_attrs:
                self.vib_artists[force_level].set_offsets([[0, 0]])

    def add_remove_actrecv(self, x_map, y_map, add=True):
        if x_map is None or y_map is None:
            return

        # convert map point to local coordinate
        if self.maptype == maptypes[1]:
            x, y = t_map_local.transform(x_map, y_map)
        else:
            x, y = x_map, y_map

        cp = tuple([x, y])
        c1 = tuple([x + offset_transformation(OFFSET_INLINE, OFFSET_CROSSLINE)[0],
                    y + offset_transformation(OFFSET_INLINE, OFFSET_CROSSLINE)[1]])
        c2 = tuple([x + offset_transformation(OFFSET_INLINE, -OFFSET_CROSSLINE)[0],
                    y + offset_transformation(OFFSET_INLINE, -OFFSET_CROSSLINE)[1]])
        c3 = tuple([x + offset_transformation(-OFFSET_INLINE, -OFFSET_CROSSLINE)[0],
                    y + offset_transformation(-OFFSET_INLINE, -OFFSET_CROSSLINE)[1]])
        c4 = tuple([x + offset_transformation(-OFFSET_INLINE, OFFSET_CROSSLINE)[0],
                    y + offset_transformation(-OFFSET_INLINE, OFFSET_CROSSLINE)[1]])

        # set corner points of active receivers and convert back to map coordinates
        if self.maptype == maptypes[1]:
            cp = t_local_map.transform(cp[0], cp[1])
            c1 = t_local_map.transform(c1[0], c1[1])
            c2 = t_local_map.transform(c2[0], c2[1])
            c3 = t_local_map.transform(c3[0], c3[1])
            c4 = t_local_map.transform(c4[0], c4[1])

        if add:
            self.actrecv_artist.set_xy(np.array([c1, c2, c3, c4]))
            self.cp_artist.center = cp

        else:
            self.actrecv_artist.set_xy(np.array([c1]))
            self.cp_artist.center = (0, 0)

    def convert_to_map(self, df):
        if self.maptype == maptypes[1] and not df.empty:
            df = df.to_crs(f'epsg:{EPSG_OSM}')
        else:
            pass
        return df

    def on_click(self, event):
        # If we're using a tool on the toolbar, don't add/draw a point...
        if self.fig.canvas.toolbar.mode != '':
            return

        # left click to add the active receivers
        if event.button == 1:
            self.add_remove_actrecv(event.xdata, event.ydata, add=True)

        # right click to remove the active receivers
        elif event.button == 3:
            self.add_remove_actrecv(event.xdata, event.ydata, add=False)

        self.blit()

    def on_key(self, event):
        if event.key not in ['right', 'left', ' ']:
            return

        logger.info(f'|------------------------| {event.key} |------------------------|')
        if event.key == 'right':
            self.date += timedelta(1)
            self.plot_pss_data(2)
            self.update_right_pss_dataframes()

        elif event.key == 'left':
            self.date -= timedelta(1)
            self.plot_pss_data(0)
            self.update_left_pss_dataframes()

        elif event.key == ' ':
            self.plot_pss_data(1)

        self.blit()

    def on_timer(self):
        print('on timer ...')
        self.timer.stop()
        self.blit()

    def on_resize(self, event):
        self.resize_timer.start()
        self.remove_artists()
        self.background = None

    def blit(self):
        if self.background is None:
            self.background = self.fig.canvas.copy_from_bbox(self.fig.bbox)
            print('wait until data is shown on the map ...')
            self.setup_artists()
            self.plot_pss_data(1)
            self.fig.canvas.draw()
            print(
                'go ahead use arrow keys to toggle date, '
                'click canvas for active receivers')
            self.resize_timer.stop()

        else:
            self.fig.canvas.restore_region(self.background)
            self.fig.draw_artist(self.date_artist)
            for force_level in force_attrs:
                self.fig.draw_artist(self.vib_artists[force_level])
            self.fig.draw_artist(self.actrecv_artist)
            self.fig.draw_artist(self.cp_artist)
            self.fig.canvas.blit(self.fig.bbox)
            self.fig.canvas.flush_events()

    def show(self, block=True):
        plt.show(block=block)


def main(maptype):
    start_date = get_date()
    PlotMap(start_date, maptype=maptype).show()

if __name__ == "__main__":
    '''  Interactive display of production. Background maps can be
         selected by giving an argument.
         :arguments:
            local: local map (jpg)
            OSM: OpenStreetMap
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
