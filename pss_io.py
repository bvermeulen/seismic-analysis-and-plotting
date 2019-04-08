import glob
import csv
import pandas as pd
import numpy as np
from geopandas import GeoDataFrame
from shapely.geometry import Point
from datetime import timedelta

from geo_io import daterange, EPSG_31256_adapted, EPSG_WGS84
from pss_attr import pss_attr
from Utils.plogger import Logger, timed
from Utils.utils import average_with_outlier_removed


PREFIX = r'RAW_PSS\PSS_'
LAT_MIN = 48
LAT_MAX = 49
LONG_MIN = 16
LONG_MAX = 18

logger = Logger.getlogger()
nl = '\n'


class PssData:
    '''  methods for handling PSS data '''

    def __init__(self, pss_input_data):
        self.pss_data = pss_input_data

        # clean PSS data
        delete_list = []
        for i, pss in enumerate(self.pss_data):
            if pss[pss_attr['Void']['col']] == 'Void':
                delete_list.append(i)
            elif not pss[pss_attr['File Num']['col']]:
                delete_list.append(i)
            elif int(pss[pss_attr['Force Avg']['col']]) == 0:
                delete_list.append(i)
            try:
                if pss[pss_attr['Comment']['col']][-10:] == 'been shot!': 
                    delete_list.append(i)
            except:
                pass
                
        for i in range(len(delete_list)-1, -1, -1):
            del self.pss_data[delete_list[i]]

        #sort pss data on File Num
        self.pss_data = sorted(self.pss_data, key=lambda x: int(x[pss_attr['File Num']['col']]))

    def determine_fleets(self):
        # determine fleets
        fleets = set()
        record = 0
        _fleet = set()
        for pss in self.pss_data:
            if int(pss[pss_attr['File Num']['col']]) == record:
                _fleet.add(int(pss[pss_attr['Unit ID']['col']]))
            else:
                record = int(pss[pss_attr['File Num']['col']])
                if _fleet:
                    fleets.add(frozenset(_fleet))
                _fleet = set()
                _fleet.add(int(pss[pss_attr['Unit ID']['col']]))
    
        fleets = list(fleets)
        fleets_copy = fleets[:]

        for i in range(len(fleets)):
            for j in range(0, len(fleets)):
                if fleets[j] > fleets[i]:
                    fleets_copy.remove(fleets[i])
                    break

        self.fleets = fleets_copy 
    
    def make_vp_gpd(self, attr_key):
        '''  method to make geopandas dataframe for records obtained 
             from values from pss
        '''
        vp_lats = []
        vp_longs = []
        vp_attributes = []
        record = 0
        _count = 0
        
        # loop over the records in pss_data and assert they are sequential
        for index, pss in enumerate(self.pss_data):
            vp_lat = float(pss[pss_attr['Lat']['col']])
            vp_long = float(pss[pss_attr['Lon']['col']])
            valid_coord = LAT_MIN < vp_lat and vp_lat < LAT_MAX and \
                          LONG_MIN < vp_long and vp_long < LONG_MAX
            if not valid_coord:
                logger.debug(f'invalid coord: record: {record}: {(LAT_MIN, LAT_MAX, LONG_MIN, LONG_MAX)},'
                             f'{(vp_lat, vp_long)}')

            vp_attr_value = float(pss[pss_attr[attr_key]['col']])
            pss_record = int(pss[pss_attr['File Num']['col']])
            if pss_record < record:
                logger.info(f'pss is not sequential at {pss_record}')

            if record == pss_record:
                if valid_coord:
                    _vp_lat += vp_lat
                    _vp_long += vp_long
                    _vp_attribute.append(vp_attr_value)
                    _count += 1
                else:
                    continue

            else:
                if _count > 0:
                    _average_attribute = average_with_outlier_removed(_vp_attribute, 
                        pss_attr[attr_key]['range'])
                    if _average_attribute != None:
                        vp_lats.append(_vp_lat / _count)
                        vp_longs.append(_vp_long / _count)
                        vp_attributes.append(_average_attribute)
                    else:
                        logger.debug(f'record: {record}, invalid list: {_vp_attribute}')

                record = pss_record
                if valid_coord:
                    _vp_lat = vp_lat
                    _vp_long = vp_long
                    _vp_attribute = [vp_attr_value]
                    _count = 1
                else:
                    _count = 0

        # and make the dataframe
        geometry = [Point(xy) for xy in zip(vp_longs, vp_lats)]
        self.vp_gpd = GeoDataFrame(crs={'init': f'epsg:{EPSG_WGS84}'}, geometry=geometry)
        self.vp_gpd = self.vp_gpd.to_crs(EPSG_31256_adapted)
        self.vp_gpd[attr_key] = vp_attributes

        logger.debug(f'vp_gpd is:{nl}{self.vp_gpd.head(10)}')

        return self.vp_gpd

    def add_force_level(self, medium_force, high_force):
        def group_forces(forces):
            ''' helper function to group forces in LOW, MEDIUM , HIGH '''
            force_levels = []
            for force in forces:
                if force > high_force:
                    force_levels.append('1HIGH')

                elif force > medium_force:
                    force_levels.append('2MEDIUM')

                elif force <= medium_force:
                    force_levels.append('3LOW')
                    
                else:
                    assert False, "this is an invalid option, check the code"
            return force_levels

        self.vp_gpd['force_level'] = group_forces(self.vp_gpd['Force Avg'].to_list())

        return self.vp_gpd

def read_pss_file_csv(csv_file):
    try:
        pss_data = []
        with open(csv_file) as csvobject:
            content = csv.reader(csvobject, delimiter=',')
            for row in content:
                pss_data.append(row)
    except FileNotFoundError:
        pss_data = -1

    return pss_data


def read_pss_file_xls(xls_file):
    try:
        pss_data = []
        df = pd.read_excel(xls_file)
        pss_data.append(list(df))
        pss_data += df.values.tolist()
    except FileNotFoundError:
        pss_data = -1
    
    return pss_data


def pss_read_file(_date):

    _pss_file = PREFIX + ''.join([f'{int(_date.strftime("%Y")):04}', '_'
                                  f'{int(_date.strftime("%m")):02}', '_' 
                                  f'{int(_date.strftime("%d")):02}', '*.csv'])
    # pss_file = PREFIX + _date + '.xlsx'

    logger.debug(f'filename: {_pss_file}')
    _pss_file = glob.glob(_pss_file)
    logger.info(f'filename: {_pss_file}')
    
    if len(_pss_file) != 1:
        pss_file = 'no_file_found'
    else:
        pss_file = _pss_file[0]

    if pss_file[-4:] == '.csv':
        pss_data = read_pss_file_csv(pss_file)
    elif pss_file[-5:] == '.xlsx':
        pss_data = read_pss_file_xls(pss_file)
    else:
        pss_data = -1

    if pss_data == -1:
        logger.debug(f'incorrect file name')

    return pss_data


def get_vps_force_for_date_range(start_date, end_date, medium_force, high_force):
    '''  reads pss data for a date range and extracts vps and force
         
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
        pss_data = pss_read_file(day)
        if pss_data == -1:
            continue
        vps = PssData(pss_data)
        vps.make_vp_gpd('Force Avg')
        vp_day_gpd = vps.add_force_level(medium_force, high_force)

        vp_gpd = pd.concat([vp_gpd, vp_day_gpd], ignore_index=True)

        logger.debug(f'length: {len(vp_day_gpd)}')

    logger.info(f'total length: {len(vp_gpd)}')

    return vp_gpd

def get_vps_attribute_for_date_range(attribute, start_date, end_date):
    '''  reads pss data for a date range and extracts vps and viscosity
         
         parameters:
         :start_date: start date (datetime date type)
         :end_date: end date (datetime date type)

         return:
         :vp_gpd: geopandas dataframe with vp attribute data in local coordinates
    '''
    vp_gpd = GeoDataFrame()

    for day in daterange(start_date, end_date):
        pss_data = pss_read_file(day)
        if pss_data == -1:
            continue
        vps = PssData(pss_data)
        vp_day_gpd = vps.make_vp_gpd(attribute)

        vp_gpd = pd.concat([vp_gpd, vp_day_gpd], ignore_index=True)

        logger.debug(f'length: {len(vp_day_gpd)}')

    logger.info(f'total length: {len(vp_gpd)}')

    return vp_gpd

