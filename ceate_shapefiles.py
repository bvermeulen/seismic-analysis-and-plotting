import geopandas as gpd
from shapely.geometry import Polygon
import matplotlib.pyplot as plt
from geo_io import df_to_excel, swath_selection
from pprint import pprint

EPSG_31256_adapted = "+proj=tmerc +lat_0=0 +lon_0=16.33333333333333"\
                     " +k=1 +x_0=+500000 +y_0=0 +ellps=bessel "\
                     "+towgs84=577.326,90.129,463.919,5.137,1.474,5.297,2.4232 +units=m +no_defs"

areas_shapefile = r'./areas_shapes/OMV_SurveyAreas_20180813_pgon.shp'
source_shapefile = r'./areas_shapes/Source_Boundary_OMV_noWE.shp'
receiver_shapefile = r'./areas_shapes/Receiver_Boundary.shp'
geo_shapefile = r'./areas_shapes/geo_shapefile.shp'

SKN_DNS_dict = {}
SKN_DNS_gpd = gpd.GeoDataFrame(SKN_DNS_dict)
SKN_DNS_gpd.crs = EPSG_31256_adapted

areas_gpd = gpd.read_file(areas_shapefile)
receiver_gpd = gpd.read_file(receiver_shapefile)
source_gpd = gpd.read_file(source_shapefile)

print(receiver_gpd.geometry)

SKN_DNS_gpd = SKN_DNS_gpd.append({'OBJECTID': 1, 'CLIENT': 'OMV 3D', 'DESCRIPTION': 'Receiver boundary'}, 
                                  ignore_index=True)
SKN_DNS_gpd.loc[0, 'geometry'] = receiver_gpd.iloc[0].geometry

SKN_DNS_gpd = SKN_DNS_gpd.append({'OBJECTID': 2, 'CLIENT': 'OMV 3D', 'DESCRIPTION': 'SKN2 source boundary'}, 
                                  ignore_index=True)
SKN_DNS_gpd.loc[1, 'geometry'] = areas_gpd[areas_gpd['OBJECTID'] == 13].iloc[0].geometry

SKN_DNS_gpd = SKN_DNS_gpd.append({'OBJECTID': 3, 'CLIENT': 'OMV 3D', 'DESCRIPTION': 'Matzen source boundary'}, 
                                  ignore_index=True)
SKN_DNS_gpd.loc[2, 'geometry'] = areas_gpd[areas_gpd['OBJECTID'] == 3].iloc[0].geometry

SKN_DNS_gpd['OBJECTID'] = SKN_DNS_gpd['OBJECTID'].astype(int)

print(SKN_DNS_gpd.head(10))
df_to_excel(SKN_DNS_gpd, r'./SKN_DNS_gpd.xlsx', append=False)
SKN_DNS_gpd.to_file(geo_shapefile)

fig, ax = plt.subplots(figsize=(10, 10))

colors = ('r', 'b', 'y', 'c')
for i in range(3):
    print(i)
    color = colors[i]
    SKN_DNS_gpd[SKN_DNS_gpd['OBJECTID'] == i+1].plot(ax=ax, facecolor='none', edgecolor=color)

plt.show()
