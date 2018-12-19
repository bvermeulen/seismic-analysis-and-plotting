import glob
import pandas as pd
from datetime import date
from Utils.plogger import Logger


PREFIX = r'autoseis_data\OUT_'

class GeoData:
    '''  method for handling Geo data '''
    def __init__(self):
        self.logger = Logger.getlogger()

    def read_geo_datafile(self, _date):
        read_is_valid = False
        _geo_file = ''.join([PREFIX, 
                            f'{_date.year:04}', f'{_date.month:02}', f'{_date.day:02}', 
                            '*.xlsx'])
        _geo_file = glob.glob(_geo_file)
        self.logger.info(f'filename: {_geo_file}')

        if len(_geo_file) != 1:
            pass
        else:
            try:
                self.geo_df = pd.read_excel(_geo_file[0])
                self.date = _date
                read_is_valid = True
            except FileNotFoundError:
                pass
        
        return read_is_valid

    def get_geo_data(self):
        return self.date, self.geo_df

def get_date():
    _date = input('date (YYMMDD) [q - quit]: ')
    if _date in ['q', 'Q']:
        exit()
    _date = date(int(_date[0:2])+2000, 
                 int(_date[2:4]), 
                 int(_date[4:6]))

    return _date
