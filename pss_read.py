import csv
import glob
import pandas as pd
import numpy as np
from datetime import timedelta
from geo_io import daterange
from Utils.plogger import Logger


PREFIX = r'RAW_PSS\PSS_'
LAT_MIN = 48
LAT_MAX = 49
LONG_MIN = 16
LONG_MAX = 18


class PssData:
    '''  method for handling PSS data '''
    def __init__(self, pss_input_data):
        self.pss_data = pss_input_data
        self.attr = {}
        self.attr['unit_id'] = int(pss_input_data[0].index('Unit ID'))
        self.attr['record_index'] = int(pss_input_data[0].index('File Num'))
        self.attr['force_avg'] = int(pss_input_data[0].index('Force Avg'))
        self.attr['void'] = int(pss_input_data[0].index('Void'))
        self.attr['comment'] = int(pss_input_data[0].index('Comment'))
        self.attr['lat'] = int(pss_input_data[0].index('Lat'))
        self.attr['long'] = int(pss_input_data[0].index('Lon'))
        self.attr['drive'] = int(pss_input_data[0].index('Force Out'))
        self.attr['param_checksum'] = int(pss_input_data[0].index('Param Checksum'))
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
    
    def vp_df(self):
        '''  method to retrieve datafram for vps
        '''
        logger = Logger.getlogger()
        vp_lats = []
        vp_longs = []
        vp_forces = []
        
        # make a list of all records
        list_record = set()
        for pss in self.pss_data:
            list_record.add(pss[self.attr['record_index']])

        list_record = list(list_record)

        # and loop over the records 
        for record in list_record:
            _vp_lat = 0
            _vp_long = 0
            _force = 0
            _count = 0
            for pss in self.pss_data:
                if record == pss[self.attr['record_index']]:
                    vp_lat = float(pss[self.attr['lat']])
                    vp_long = float(pss[self.attr['long']])
                    valid_coord = vp_lat > LAT_MIN and vp_lat < LAT_MAX and \
                                  vp_long > LONG_MIN and vp_long < LONG_MAX
                    if valid_coord:
                        _vp_lat += float(pss[self.attr['lat']])
                        _vp_long += float(pss[self.attr['long']])
                        _force += float(pss[self.attr['force_avg']])
                        _count += 1
                    else:
                        logger.info(f'invalid coord: record: {record}: {(LAT_MIN, LAT_MAX, LONG_MIN, LONG_MAX)},'
                                    f'{(vp_lat, vp_long)}')
            try:
                _vp_lat /= _count
                _vp_long /= _count
                _force /= _count
                vp_lats.append(_vp_lat)
                vp_longs.append(_vp_long)
                vp_forces.append(_force)

            except ZeroDivisionError:
                pass

        logger.debug(f'(vp_lat, vp_long, force): {list(zip(vp_lats, vp_longs, vp_forces))}')
        return vp_longs, vp_lats, vp_forces


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
    logger = Logger.getlogger()

    _pss_file = PREFIX + ''.join([f'{int(_date.strftime("%Y")):04}', '_'
                                  f'{int(_date.strftime("%m")):02}', '_' 
                                  f'{int(_date.strftime("%d")):02}', '*.csv'])
    # pss_file = PREFIX + _date + '.xlsx'

    logger.info(f'filename: {_pss_file}')
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


def read_pss_for_date_range(start_date, end_date):
    '''  reads pss data for a date range - interactive input through console
    parameters:
    :start_date: start date (datetime date type)
    :end_date: end date (datetime date type)
    return:
    :vp_lats: numpy array 
    :vp_longs: numpy array
    :vp_forces: numpy array
    '''
    logger = Logger.getlogger()
    
    vp_lats = np.array([])
    vp_longs = np.array([])
    vp_forces = np.array([])

    for day in daterange(start_date, end_date):
        pss_data = pss_read_file(day)
        if pss_data == -1:
            continue
        pss = PssData(pss_data)
        _vp_longs, _vp_lats, _forces = pss.vp_df()
        vp_lats = np.append(vp_lats, _vp_lats)
        vp_longs = np.append(vp_longs, _vp_longs)
        vp_forces = np.append(vp_forces, _forces)
        logger.info(f'length: {len(_vp_lats)}')

    logger.info(f'total length: {len(vp_lats)}')

    return vp_longs, vp_lats, vp_forces
