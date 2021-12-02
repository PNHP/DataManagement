from arcgis.gis import GIS
from arcgis.features import FeatureLayer
url_gis = r'https://maps.waterlandlife.org:7443/arcgis'
url_fl = r'https://maps.waterlandlife.org/arcgis/rest/services/PNHP/CPP/FeatureServer/0'
user = 'mmooreWPC'
pwd = 'Nik0C@tMe0w'
fgdb = 'memory'
fc = 'test'
gis = GIS(url_gis, user, pwd)
fl = FeatureLayer(url_fl)
fs = fl.query()
fs.save(fgdb, fc)‍‍‍‍‍‍‍‍‍‍‍‍‍‍