from geo_io import get_date_range, daterange, get_date
from pss_plot import pss_plot_function
from Utils.plogger import Logger

logger = Logger.getlogger()
nl = '\n'

if __name__ == "__main__":
    logger.info(f'{nl}========================================'\
                f'{nl}===>   Running: pss_plot_range.py   <==='\
                f'{nl}========================================')

    initial_date = get_date()

    start_date = -1
    while start_date == -1:
        start_date, end_date = get_date_range()

    for day in daterange(start_date, end_date):
        pss_plot_function(initial_date, day, swaths_selected=[0], saveplot=True)
