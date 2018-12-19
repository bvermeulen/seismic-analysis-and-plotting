from geo_read import GeoData, get_date
from pprint import pprint
import pandas as pd
import numpy as np
from Utils.plogger import Logger

def geo_plot_main():
    gd = GeoData()
    geo_df = -1
    while not gd.read_geo_datafile(get_date()):
        pass
    
    _date, geo_df = gd.get_geo_data()
    _date.isoformat()


    # convert 'SAVED_TIMESTAMP' to pandas timestamp
    geo_df['SAVED_TIMESTAMP'] = pd.to_datetime(geo_df['SAVED_TIMESTAMP'])

    for _, row in geo_df.iterrows():
        if row['SAVED_TIMESTAMP'].date() == _date:
            print(row['SAVED_TIMESTAMP'], row['GP_TODO'])

    pprint(geo_df)
    pprint(str(_date))


if __name__ == "__main__":
    logformat = '%(asctime)s - %(levelname)s - %(message)s'
    Logger.set_logger('geo_plot.log', logformat, 'DEBUG')
    geo_plot_main()