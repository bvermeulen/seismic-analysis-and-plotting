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
ALLOWED_FORCE_RANGE = 12

logger = Logger.getlogger()
nl = '\n'


class PssData:
    '''  method for handling PSS data '''
    def __init__(self, pss_input_data, medium_force, high_force):
        self.pss_data = pss_input_data
        self.medium_force = medium_force
        self.high_force = high_force 

        self.attr = {}
        self.attr['unit_id'] = int(self.pss_data[0].index('Unit ID'))
        self.attr['record_index'] = int(self.pss_data[0].index('File Num'))
        self.attr['force_avg'] = int(self.pss_data[0].index('Force Avg'))
        self.attr['void'] = int(self.pss_data[0].index('Void'))
        self.attr['comment'] = int(self.pss_data[0].index('Comment'))
        self.attr['lat'] = int(self.pss_data[0].index('Lat'))
        self.attr['long'] = int(self.pss_data[0].index('Lon'))
        self.attr['drive'] = int(self.pss_data[0].index('Force Out'))
        self.attr['param_checksum'] = int(self.pss_data[0].index('Param Checksum'))
        del self.pss_data[0]

        # clean PSS data
        delete_list = []
        for i, pss in enumerate(self.pss_data):
            if pss[self.attr['void']] == 'Void':
                delete_list.append(i)
            elif not pss[self.attr['record_index']]:
                delete_list.append(i)
            elif int(pss[self.attr['force_avg']]) == 0:
                delete_list.append(i)
            try:
                if pss[self.attr['comment']][-10:] == 'been shot!': 
                    delete_list.append(i)
            except:
                pass
                
        for i in range(len(delete_list)-1, -1, -1):
            del self.pss_data[delete_list[i]]
            
    def determine_fleets(self):
        # determine fleets
        fleets = set()
        record = 0
        _fleet = set()
        for pss in self.pss_data:
            if int(pss[self.attr['record_index']]) == record:
                _fleet.add(int(pss[self.attr['unit_id']]))
            else:
                record = int(pss[self.attr['record_index']])
                if _fleet:
                    fleets.add(frozenset(_fleet))
                _fleet = set()
                _fleet.add(int(pss[self.attr['unit_id']]))
    
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
        
        # make a list of all unique records and sort 
        list_record = set()
        for pss in self.pss_data:
            list_record.add(pss[self.attr['record_index']])

        list_record = list(list_record)
        list_record.sort()
        _index = 0

        # and loop over the records 
        for record in list_record:
            _vp_lat = 0
            _vp_long = 0
            _forces = []
            _count = 0

            # loop over a narrow range of pss_data records starting at where
            # last loop stopped
            for index, pss in enumerate(self.pss_data[_index:]):
                if record == pss[self.attr['record_index']]:
                    vp_lat = float(pss[self.attr['lat']])
                    vp_long = float(pss[self.attr['long']])
                    valid_coord = vp_lat > LAT_MIN and vp_lat < LAT_MAX and \
                                  vp_long > LONG_MIN and vp_long < LONG_MAX
                    if valid_coord:
                        _vp_lat += float(pss[self.attr['lat']])
                        _vp_long += float(pss[self.attr['long']])
                        _forces.append(float(pss[self.attr['force_avg']]))
                        _count += 1
                    else:
                        logger.debug(f'invalid coord: record: {record}: {(LAT_MIN, LAT_MAX, LONG_MIN, LONG_MAX)},'
                                    f'{(vp_lat, vp_long)}')
                else:
                    # as pss_data record numbers are sequentially stop the loop  
                    # as soon as this is greater than the currect record number
                    # and set a new index start value
                    if pss[self.attr['record_index']] > record:
                        _index += index
                        break  

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
        logger.info(f'incorrect file name')

    return pss_data


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
        pss_data = pss_read_file(day)
        if pss_data == -1:
            continue
        vp_day_gpd = PssData(pss_data, medium_force, high_force).make_vp_gpd()
        vp_gpd = pd.concat([vp_gpd, vp_day_gpd], ignore_index=True)

        logger.debug(f'length: {len(vp_day_gpd)}')

    logger.info(f'total length: {len(vp_gpd)}')

    return vp_gpd
