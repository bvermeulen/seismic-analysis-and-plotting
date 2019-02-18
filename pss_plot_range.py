from datetime import date
from geo_io import get_date_range, daterange
from pss_plot import pss_plot_function
from Utils.plogger import Logger

logger = Logger.getlogger()
nl = '\n'

if __name__ == "__main__":
    logger.info(f'{nl}========================================'\
                f'{nl}===>   Running: pss_plot_range.py   <==='\
                f'{nl}========================================')

    initial_date = date(2018, 10, 15)  # first date production

    start_date = -1
    while start_date == -1:
        start_date, end_date = get_date_range()

    for day in daterange(start_date, end_date):
        pss_plot_function(initial_date, day, swaths_selected=[0], saveplot=True)
