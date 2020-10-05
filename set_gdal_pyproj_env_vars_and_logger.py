import os
from Utils.plogger import Logger

'''  for some reason the GDAL_DATA and PROJ_LIB environment variables are not set properly
     this module to be called at the very start of the program

     as this is the first module to be called logger is also set
'''
# os.environ['GDAL_DATA'] = os.environ['CONDA_PREFIX'] + r'\Library\share\gdal'
# os.environ['PROJ_LIB'] = os.environ['CONDA_PREFIX'] + r'\Library\share'

# start logger
logformat = '%(asctime)s - %(levelname)s - %(message)s'
Logger.set_logger('autoseis.log', logformat, 'INFO')
logger = Logger.getlogger()

# logger.debug(f'GDAL_DATA={os.environ["GDAL_DATA"]}')
# logger.debug(f'PROJ_LIB={os.environ["PROJ_LIB"]}')
