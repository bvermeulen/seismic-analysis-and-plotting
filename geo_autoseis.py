import set_gdal_pyproj_env_vars_and_logger
from geo_io import GeoData, get_date, df_to_excel
import pandas as pd
import numpy as np
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
import matplotlib.pyplot as plt
import collections
from datetime import date
from Utils.plogger import Logger
from Utils.utils import string_to_value_or_nan
import inspect


# business rules
thresholdtype1 = 25
thresholdtype2 = 15
th_high = 10
th_mid = 5
th_low = 0

# other constants
logger = Logger.getlogger()
EXCEL_SUMMARY_FILE = 'autoseis_summary.xlsx'
NO_VALUE = 999


def calculate_bat_status(geo_df):
    '''  extracts battery status with respect to days in field
         input: geo_df
         return: 3 lists: list days in field type 1, list days in field type 2
                          list days over threshold
    '''
    days_in_field = geo_df['days_in_field'].tolist()
    bat_types = geo_df['Battype'].tolist()
    assert len(days_in_field) == len(bat_types), "check match battype and days_in_field"

    days_in_field_type1, days_in_field_type2, days_over_threshold = [], [], []
    for bat in zip(bat_types, days_in_field):
        try:
            bat_type = int(bat[0])
        except ValueError:
            logger.info(f'{inspect.stack()[0][3]} - Exception ValueError: {bat}')
            bat_type = 0
            
        if pd.isnull(bat[1]) or bat_type not in [1, 2]:
            days_in_field_type1.append(np.NaN)
            days_in_field_type2.append(np.NaN)
            days_over_threshold.append(np.NaN)

        elif bat_type == 1:
            days_in_field_type1.append(bat[1])
            days_in_field_type2.append(np.NaN)
            days_over_threshold.append(bat[1] - thresholdtype1)

        elif bat_type == 2:
            days_in_field_type1.append(np.NaN)
            days_in_field_type2.append(bat[1])
            days_over_threshold.append(bat[1] - thresholdtype2)

        else:
            assert False, "this option cannot happen, check your code"

    return days_in_field_type1, days_in_field_type2, days_over_threshold


def geo_stats(_date, swaths, geo_df):
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
                    'Perc. bad': 0,
                    'total bats': 0,
                    f'bats {th_low}d': 0,
                    f'bats {th_mid}d': 0,
                    f'bats {th_high}d': 0,
                    'swaths': ''}

    # make list of 'GP_TODO' column for rows for specific date '_date'
    geo_status = geo_df[pd.to_datetime(geo_df['SAVED_TIMESTAMP']).dt.date == _date]['GP_TODO'].tolist()

    # get the list of batteries days over threshold
    _, _, days_over_threshold = calculate_bat_status(geo_df)

    total = 0
    total_error = 0
    for key, _ in status_codes.items():
        count = geo_status.count(key)
        status_codes[key] = count
        total += count
        if 'needed' in key:
            total_error += count

    status_codes['total bats'] = len(days_over_threshold)
    for days in days_over_threshold:
        if days >= th_high:
            status_codes[f'bats {th_high}d'] += 1

        elif days >= th_mid:
            status_codes[f'bats {th_mid}d'] += 1

        elif days >= th_low:
            status_codes[f'bats {th_low}d'] +=1


    # only one field has to be given as list, so dict status_codes can be readily converted to the pandas DataFrame
    # rest of values can be scalars
    status_codes['Date'] = [_date]  # for formatted date use _date.strftime('%d-%m-%y')
    status_codes['Total'] = total
    status_codes['Total ex pickup'] = total - status_codes['PICKUP all']
    try:
        status_codes['Perc. bad'] = total_error / status_codes['Total ex pickup']
    except ZeroDivisionError:
        logger.info(f'{inspect.stack()[0][3]} - Exception ZeroDivisionError: {total_error}')
        status_codes['Perc. bad'] = np.NaN
    
    status_codes['swaths'] = ', '.join([str(swath) for swath in swaths])

    # save the summary to excel
    logger.info(f'date: {_date} -- status codes:\n{status_codes}')
    df_to_excel(pd.DataFrame(status_codes),EXCEL_SUMMARY_FILE, 
                       index=False, header=False, append=True)
    

def output_bat_status_to_excel(geo_df):

    _, _, days_over_threshold = calculate_bat_status(geo_df)
    
    logger.info(f"count:\n{geo_df.count()}"
                f"\nlength days_over_threshold {len(days_over_threshold)}")

    bat_status_list = {'Date': [], 
                       'Line': [],
                       'Station': [],
                       'LocalEasting': [],
                       'LocalNorthing': [],
                       'Bat_type': [],
                       'Days_in_field': [],
                       'Daysoverthreshold': [],
                      }

    for index, row in geo_df.iterrows():
        bat_status_list['Date'].append(string_to_value_or_nan(row['OUTDATE'], 'date'))
        bat_status_list['Line'].append(string_to_value_or_nan(str(row['STATIONVIX'])[0:4], 'int'))
        bat_status_list['Station'].append(string_to_value_or_nan(str(row['STATIONVIX'])[4:8], 'int'))
        bat_status_list['LocalEasting'].append(string_to_value_or_nan(row['LocalEasti'], 'float'))
        bat_status_list['LocalNorthing'].append(string_to_value_or_nan(row['LocalNorth'], 'float'))
        bat_status_list['Bat_type'].append(string_to_value_or_nan(row['Battype'], 'int'))
        bat_status_list['Days_in_field'].append(string_to_value_or_nan(row['days_in_field'], 'int'))
        if not pd.isnull(days_over_threshold[index]):
            bat_status_list['Daysoverthreshold'].append(string_to_value_or_nan(days_over_threshold[index], 'int'))
        else:
            bat_status_list['Daysoverthreshold'].append(NO_VALUE)

    nl ='\n'
    logger.info(f"{nl}length Date: {len(bat_status_list['Date'])}"
                f"{nl}length Line: {len(bat_status_list['Line'])}"
                f"{nl}length Station: {len(bat_status_list['Station'])}"
                f"{nl}length LocalEasting: {len(bat_status_list['LocalEasting'])}"
                f"{nl}length LocalNorthing: {len(bat_status_list['LocalNorthing'])}"
                f"{nl}length Bat_type: {len(bat_status_list['Bat_type'])}"
                f"{nl}length Days_in_field: {len(bat_status_list['Days_in_field'])}"
                f"{nl}length Daysoverthreshold: {len(bat_status_list['Daysoverthreshold'])}"
               ) 

    bat_df = pd.DataFrame(bat_status_list)
    filename = ''.join([_date.strftime('%Y%m%d')[2:9], '_bat_status.xlsx'])
    df_to_excel(bat_df, filename=filename, index=False, header=True, append=False)
    

def bat_histogram(geo_df):

    days_in_field_type1, days_in_field_type2, days_over_threshold =\
        calculate_bat_status(geo_df)
    logger.info(f"count:\n{geo_df.count()}")

    bins = 40
    maxvalue = 4500
    plt.subplot(221)
    plt.hist(days_in_field_type1, bins, facecolor='g', alpha=0.5)
    plt.title(f"Bats type 1: {_date.strftime('%d %b %Y')}")
    plt.xlabel('Days')
    plt.ylabel('Stations')
    plt.axis([0, bins, 0, maxvalue])
    plt.grid(True)

    plt.subplot(222)
    plt.hist(days_in_field_type2, bins, facecolor='r', alpha=0.5)
    plt.title(f"Bats type 2: {_date.strftime('%d %b %Y')}")
    plt.xlabel('Days')
    plt.axis([0, bins, 0, maxvalue])
    plt.grid(True)

    bins = 60
    plt.subplot(223)
    plt.hist(days_over_threshold, bins, facecolor='b', alpha=0.5)
    plt.title(f"Threshold days: {_date.strftime('%d %b %Y')}")
    plt.xlabel('Days')
    plt.axis([-bins/2, bins/2, 0, maxvalue])
    plt.grid(True)

    plt.subplots_adjust(hspace=0.10, wspace=0.10)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":

    nl = '\n'
    logger.info(f'{nl}==========================+======='\
                f'{nl}===> Running: geo_autoseis.py <==='\
                f'{nl}==================================')

    gd = GeoData()

    # extract geo data by date
    valid = False
    while not valid:
        _date = get_date()
        valid = gd.read_geo_data(_date)

    swaths, geo_df, _ , _ = gd.filter_geo_data_by_swaths()

    if input('Summarise geo date? [Y/N] ')[0] in ['y', 'Y']:
        geo_stats(_date, swaths, geo_df)
    
    output_bat_status_to_excel(geo_df)
    bat_histogram(geo_df)
