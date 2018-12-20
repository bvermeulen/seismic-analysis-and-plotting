from geo_read import GeoData, get_date
from pprint import pprint
import pandas as pd
import numpy as np
import collections
from Utils.plogger import Logger

status_codes = collections.OrderedDict()
status_codes = {'Date': '',
                'Battery changed 20 Ah / OK': 0,
                'Battery changed 30 Ah / OK': 0,
                'Checked / OK': 0, 
                'New 1 String needed': 0,
                'New 2 Strings needed': 0,
                'New Battery needed': 0,
                'New HDR needed': 0,
                'New HDR/Battery needed': 0,
                'New Peg needed': 0,
                'PICKUP all': 0,
                'checked, but to be checked again': 0,
                'Total': 0,
                'Total ex pickup': 0,
                'Perc. bad': 0,}

def geo_stats():
    logger = Logger.getlogger()
    gd = GeoData()
    while not gd.read_geo_datafile(get_date()):
        pass
    
    _date, geo_df = gd.get_geo_data()

    # make list of 'GP_TODO' column for rows with '_date'
    geo_status = geo_df[pd.to_datetime(geo_df['SAVED_TIMESTAMP']).dt.date == _date]['GP_TODO'].tolist()

    total = 0
    total_error = 0
    for key, _ in status_codes.items():
        if key not in ['Date', 'Total', 'Perc. bad']:
            count = geo_status.count(key)
            status_codes[key] = [count]
            total += count
            if 'needed' in key:
                total_error += count
        
    status_codes['Date'] = [_date]  # for formatted date use _date.strftime('%d-%m-%y')
    status_codes['Total'] = [total]
    status_codes['Total ex pickup'] = [total - status_codes['PICKUP all'][0]]
    try:
        status_codes['Perc. bad'] = [total_error / status_codes['Total ex pickup'][0]]
    except ZeroDivisionError:
        status_codes['Perc. bad'] = ['NaN']

    logger.info(status_codes)    
    status_codes_df = pd.DataFrame(status_codes)
    gd.append_df_to_excel(status_codes_df, index=False, header=False)


if __name__ == "__main__":
    logformat = '%(asctime)s - %(levelname)s - %(message)s'
    Logger.set_logger('geo_autoseis.log', logformat, 'DEBUG')
    geo_stats()