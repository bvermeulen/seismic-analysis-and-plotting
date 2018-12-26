from geo_io import GeoData, get_date, get_date_range, daterange, append_df_to_excel
from pprint import pprint
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import collections
from Utils.plogger import Logger


th_high = 10
th_mid = 5
th_low = 0


def geo_stats(_date, geo_df):
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
                    f'bats {th_high}d': 0}
    logger = Logger.getlogger()

    # make list of 'GP_TODO' column for rows for specific date '_date'
    geo_status = geo_df[pd.to_datetime(geo_df['SAVED_TIMESTAMP']).dt.date == _date]['GP_TODO'].tolist()
    # make list of number of days over threshold
    bat_status = [val for val in geo_df['days_over_threshold'].tolist() if not pd.isnull(val)]

    total = 0
    total_error = 0
    for key, _ in status_codes.items():
        count = geo_status.count(key)
        status_codes[key] = count
        total += count
        if 'needed' in key:
            total_error += count

    status_codes['total bats'] = len(bat_status)
    for days in bat_status:
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
        status_codes['Perc. bad'] = np.NaN

    logger.info(f'date: {_date} -- status codes:\n{status_codes}')
    append_df_to_excel(pd.DataFrame(status_codes), index=False, header=False)


def summarise_geo_data():
    start_date = -1
    gd = GeoData()
    while start_date == -1:
        start_date, end_date = get_date_range()
    
    for _date in daterange(start_date, end_date):
        valid, geo_df = gd.read_geo_data(_date)
        if valid:
            geo_stats(_date, geo_df)


def bat_histogram():
    logger = Logger.getlogger()
    gd = GeoData()
    valid = False
    while not valid:
        _date = get_date()
        valid, geo_df = gd.read_geo_data(_date)

    days_in_field_type1 = geo_df['days_in_field_type1'].tolist()
    days_in_field_type2 = geo_df['days_in_field_type2'].tolist()
    days_over_threshold = geo_df['days_over_threshold'].tolist()
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
    logformat = '%(asctime)s - %(levelname)s - %(message)s'
    Logger.set_logger('geo_autoseis.log', logformat, 'DEBUG')

    answer = input('Summarise geo date? [Y/N] ')
    if answer in ['y', 'Y', 'yes', 'Yes', 'YES']:
        summarise_geo_data()
    
    answer = input('Display histogram? [Y/N] ')
    if answer in ['y', 'Y', 'yes', 'Yes', 'YES']:
        bat_histogram()
