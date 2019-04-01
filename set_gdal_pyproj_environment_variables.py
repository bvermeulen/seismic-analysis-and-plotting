import os

# for some reason the GDAL_DATA and PROJ_LIB environment variables are not set properly
# this module to be called at the very start of the program
os.environ['GDAL_DATA'] = os.environ['CONDA_PREFIX'] + r'\Library\share\gdal'
print(f'GDAL_DATA={os.environ["GDAL_DATA"]}')
os.environ['PROJ_LIB'] = os.environ['CONDA_PREFIX'] + r'\Library\share'
print(f'PROJ_LIB={os.environ["PROJ_LIB"]}')

