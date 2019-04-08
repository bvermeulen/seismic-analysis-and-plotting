Set of program tools to list and plot geophone and vibro attributes:
   bat_plot.py - plot battery status
   geo_autoseis.py - provide summary list to excel of checked stations
   geo_plot.py - plot stations that have been checked
   pss_data.py - analysed pss data on attributes phase, force and distortion
   pss_plot_attribute.py - plot a pss attribute for date range on screen
   pss_plot_day.py - plot force on screen interactively
   pss_plot_range.py - saves image of force for date range either single days or cumulative

Note there may be issues with gdal and pyproj

As a resolution create the following environment variables to set the correct paths for GDAL_DATA and PROJ_LIB:

GDAL_DATA=c:\users\user\anaconda3\envs\geo_env\Library\share\gdal   
PROJ_LIB=c:\users\user\anaconda3\envs\geo_env\Library\share

or as done here the environment variables are set in the module set_gdal_pyproj_environment_variables.py

   os.environ['GDAL_DATA'] = os.environ['CONDA_PREFIX'] + r'\Library\share\gdal'   
   os.environ['PROJ_LIB'] = os.environ['CONDA_PREFIX'] + r'\Library\share'

