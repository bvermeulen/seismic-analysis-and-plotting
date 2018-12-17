# projection example
# The answer might be helpful for others so I have posted my solution. I found pyproj works better then utm. In pyproj we can specify utm zone.
# import pyproj
from pyproj import Proj
from pprint import pprint
from utm import latlon_to_zone_number

longs = [16.01783828, 17.0086323, 16.4784]
lats =  [48.09774797, 48.55559181, 48.231]
zone_number = latlon_to_zone_number(lats[0], longs[1])
pprint(f'zone number: {zone_number}')

pprint(f'longitudes: {longs}, latitudes: {lats}')

epsg = 31286
myProj = Proj(init=f'EPSG:{epsg}')
eastings, northings = myProj(longs, lats) 
pprint(f'eastings: {eastings}, northings: {northings}')

eastings_crs = [575782.1956641411, 648215.3421904881]
northings_crs = [5327665.617543304, 5380002.786198429]
pprint(f'crs transform')
pprint(f'eastings crs: {eastings_crs}, northings crs {northings_crs}')


'''
0  POINT (16.01783828 48.09774797)
1   POINT (17.0086323 48.55559181)
2018-12-14 12:11:21,086 - INFO -                                       geometry
0  POINT (575782.1956641411 5327665.617543304)
1  POINT (648215.3421904881 5380002.786198429)
2018-12-14 12:11:21,319 - INFO - (575782.1956641411, 648215.3421904881, 5327665.617543304, 5380002.786198429)
'''