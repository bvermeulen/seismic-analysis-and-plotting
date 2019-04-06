import csv
import glob
import pandas as pd
import numpy as np
from geopandas import GeoDataFrame
from shapely.geometry import Point
from datetime import timedelta

from geo_io import daterange, EPSG_31256_adapted, EPSG_WGS84
from Utils.plogger import Logger
from Utils.utils import average_with_outlier_removed


PREFIX = r'RAW_PSS\PSS_'
LAT_MIN = 48
LAT_MAX = 49
LONG_MIN = 16
LONG_MAX = 18
ALLOWED_FORCE_RANGE = 10

logger = Logger.getlogger()
nl = '\n'


class PssData:
    '''  method for handling PSS data '''
    def __init__(self, pss_df, medium_force, high_force):
        self.pss_df = pss_df
        self.medium_force = medium_force
        self.high_force = high_force

        # self.pss_df['Comment'] = self.pss_df['Comment'].astype('str')
        # self.pss_df['Void'] = self.pss_df['Void'].astype('str')

        # clean PSS data
        delete_list = []
        for index, pss_row in self.pss_df.iterrows():
            if pss_row['Void'] == 'Void':
                delete_list.append(index)
            elif pd.isnull(pss_row['File Num']):
                delete_list.append(index)
            elif pss_row['Force Avg'] == 0:
                delete_list.append(index)
            try:
                if pss_row['Comment'][-10:] == 'been shot!':
                    print('hello comment') 
                    delete_list.append(index)
            except:
                pass

        self.pss_df = self.pss_df.drop(delete_list).reset_index()

        # set the proper types
        self.pss_df['File Num'] = self.pss_df['File Num'].astype('int64')

    def get_pss_df(self):
        return self.pss_df

    def determine_fleets(self):
        # determine fleets
        fleets = set()
        record = 0
        _fleet = set()
        for _, pss_row in self.pss_df.iterrows():
            if pss_row['File Num'] == record:
                _fleet.add(pss_row['Unit ID'])
            else:
                record = pss_row['File Num']
                if _fleet:
                    fleets.add(frozenset(_fleet))
                _fleet = set()
                _fleet.add(pss_row['Unit ID'])
    
        fleets = list(fleets)
        fleets_copy = fleets[:]

        for i in range(len(fleets)):
            for j in range(0, len(fleets)):
                if fleets[j] > fleets[i]:
                    fleets_copy.remove(fleets[i])
                    break

        self.fleets = fleets_copy 
    
    def make_vp_gpd(self):
        '''  method to make geopandas dataframe for records obtained 
             from values from pss
        '''
        vp_lats = []
        vp_longs = []
        vp_forces = []
        
        # make a list of all records
        list_record = set()
        for _, pss_row in self.pss_df.iterrows():
            list_record.add(pss_row['File Num'])

        list_record = list(list_record)

        # and loop over the records 
        for record in list_record:
            _vp_lat = 0
            _vp_long = 0
            _forces = []
            _count = 0
            _pss_sub_df = self.pss_df.loc[self.pss_df['File Num'] == record, 
                                      {'Lat', 'Lon', 'Force Avg'}]
            for _, pss_row in _pss_sub_df.iterrows():
                vp_lat = pss_row['Lat']
                vp_long = pss_row['Lon']
                valid_coord = vp_lat > LAT_MIN and vp_lat < LAT_MAX and \
                              vp_long > LONG_MIN and vp_long < LONG_MAX
                if valid_coord:
                    _vp_lat += pss_row['Lat']
                    _vp_long += pss_row['Lon']
                    _forces.append(pss_row['Force Avg'])
                    _count += 1
                else:
                    logger.debug(f'invalid coord: record: {record}: {(LAT_MIN, LAT_MAX, LONG_MIN, LONG_MAX)},'
                                 f'{(vp_lat, vp_long)}')
                                    
            if _count > 0:
                _average_force = average_with_outlier_removed(_forces, 
                                    ALLOWED_FORCE_RANGE)
                if _average_force:
                    vp_lats.append(_vp_lat / _count)
                    vp_longs.append(_vp_long / _count)
                    vp_forces.append(_average_force)
                else:
                    logger.info(f'record: {record}, invalid list of forces: {_forces}')
            else:
                pass

        # and make the dataframe
        geometry = [Point(xy) for xy in zip(vp_longs, vp_lats)]
        self.vp_gpd = GeoDataFrame(crs={'init': f'epsg:{EPSG_WGS84}'}, geometry=geometry)
        self.vp_gpd = self.vp_gpd.to_crs(EPSG_31256_adapted)
        self.vp_gpd['forces'] = vp_forces
        self.add_force_level()

        logger.debug(f'vp_gpd is:{nl}{self.vp_gpd.head(10)}')

        return self.vp_gpd

    def add_force_level(self):
        def group_forces(forces):
            ''' helper function to group forces in LOW, MEDIUM , HIGH '''
            force_levels = []
            for force in forces:
                if force > self.high_force:
                    force_levels.append('1HIGH')

                elif force > self.medium_force:
                    force_levels.append('2MEDIUM')

                elif force <= self.medium_force:
                    force_levels.append('3LOW')
                    
                else:
                    assert False, "this is an invalid option, check the code"
            return force_levels

        self.vp_gpd['force_level'] = group_forces(self.vp_gpd['forces'].to_list())


def read_pss_file_csv(csv_file):
    try:
        pss_df = pd.read_csv(csv_file)
    except FileNotFoundError:
        pss_df = pd.DataFrame()

    return pss_df


def read_pss_file_xls(xls_file):
    try:
        pss_df = pd.read_excel(xls_file)
    except FileNotFoundError:
        pss_df = pd.DataFrame()
    
    return pss_df


def pss_read_file(_date):

    _pss_file = PREFIX + ''.join([f'{int(_date.strftime("%Y")):04}', '_'
                                  f'{int(_date.strftime("%m")):02}', '_' 
                                  f'{int(_date.strftime("%d")):02}', '*.csv'])
    # pss_file = PREFIX + _date + '.xlsx'

    logger.debug(f'filename: {_pss_file}')
    _pss_file = glob.glob(_pss_file)
    logger.info(f'filename: {_pss_file}')
    
    if len(_pss_file) != 1:
        pss_file = ''
    else:
        pss_file = _pss_file[0]

    if pss_file[-4:] == '.csv':
        pss_df = read_pss_file_csv(pss_file)
    elif pss_file[-5:] == '.xlsx':
        pss_df = read_pss_file_xls(pss_file)
    else:
        pss_df = pd.DataFrame()

    if pss_df.empty:
        logger.info(f'No data for date: {_date}')

    return pss_df


def obtain_vps_for_date_range(start_date, end_date, medium_force, high_force):
    '''  reads pss data for a date range and extracts vps
         
         parameters:
         :start_date: start date (datetime date type)
         :end_date: end date (datetime date type)
         :medium_force: force level below is low force
         :high_force: force level above is high force

         return:
         :vp_gpd: geopandas dataframe with vp attribute data in local coordinates
    '''
    vp_gpd = GeoDataFrame()

    for day in daterange(start_date, end_date):
        pss_df = pss_read_file(day)
        if pss_df.empty:
            continue
        vp_day_gpd = PssData(pss_df, medium_force, high_force).make_vp_gpd()
        vp_gpd = pd.concat([vp_gpd, vp_day_gpd], ignore_index=True)

        logger.debug(f'length: {len(vp_day_gpd)}')

    logger.info(f'total length: {len(vp_gpd)}')

    return vp_gpd
