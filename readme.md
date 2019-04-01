Note there may be issues with gdal and pyproj

As a resolution create the following environment variables to set the correct paths for GDAL_DATA and PROJ_LIB:

GDAL_DATA=c:\users\user\anaconda3\envs\geo_env\Library\share\gdal   
PROJ_LIB=c:\users\user\anaconda3\envs\geo_env\Library\share

or as done here the environment variables are set in the module set_gdal_pyproj_environment_variables.py

   os.environ['GDAL_DATA'] = os.environ['CONDA_PREFIX'] + r'\Library\share\gdal'   
   os.environ['PROJ_LIB'] = os.environ['CONDA_PREFIX'] + r'\Library\share'

