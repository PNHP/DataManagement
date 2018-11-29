import arcpy, time, datetime, os
from datetime import datetime

arcpy.env.workspace = r'in_memory'

# Set tools to overwrite existing outputs
arcpy.env.overwriteOutput = True

spec_id_tbl = r'H:\Projects\CPP\Specs\SpecID_Table_20170515.csv' # this should be in .csv format
outPath = r'C:\Users\mmoore\Documents\ArcGIS\Default.gdb'
scratch = r'C:\Users\mmoore\Documents\ArcGIS\Default.gdb'

BioticsGDB = r'W:\Heritage\Heritage_Data\Biotics_datasets.gdb'
eo_ptreps = os.path.join(BioticsGDB, 'eo_ptreps')
srcfeatures = ['eo_sourceln', 'eo_sourcept', 'eo_sourcepy']
sfs = ['line', 'point', 'poly']

for srcfeature, sf in zip(srcfeatures, sfs):
    fc = os.path.join(BioticsGDB, srcfeature)
    sf = arcpy.TableToTable_conversion(fc, r'in_memory', sf)

sf = arcpy.Merge_management(sfs, os.path.join(scratch, 'sf'))
lu_query = "(LU_DIST >= 2500 AND LU_UNIT = 'METERS') OR (LU_DIST >= 1.553428 AND LU_UNIT = 'MILES') OR (LU_DIST >= 8202.1 AND LU_UNIT = 'FEET')"
sf_lu = arcpy.TableToTable_conversion(sf, r'in_memory', 'sf_lu', lu_query)

sf_count = arcpy.Statistics_analysis(sf, os.path.join(r'in_memory', 'sf_count'), 'EO_ID COUNT', 'EO_ID')
sf_lu_count = arcpy.Statistics_analysis(sf_lu, os.path.join(r'in_memory', 'sf_lu_count'), 'EO_ID COUNT', 'EO_ID')

arcpy.JoinField_management(sf_lu_count, 'EO_ID', sf_count, 'EO_ID', 'COUNT_EO_ID')

arcpy.AddField_management(sf_lu_count, 'LU_exclude', 'TEXT', '', '', 1)
with arcpy.da.UpdateCursor(sf_lu_count, ['COUNT_EO_ID', 'COUNT_EO_ID_1', 'LU_exclude']) as cursor:
    for row in cursor:
        if row[0] == row[1]:
            row[2] = 'Y'
        else:
            row[2] = 'N'
        cursor.updateRow(row)

ptreps = arcpy.FeatureClassToFeatureClass_conversion(eo_ptreps, 'in_memory', 'ptreps')
arcpy.JoinField_management(ptreps, 'EO_ID', sf_lu_count, 'EO_ID', 'LU_exclude')

cpp_eo_ptreps = arcpy.FeatureClassToFeatureClass_conversion(ptreps, outPath, 'cpp_eo_ptreps', "(((ELCODE LIKE 'AB%' AND LASTOBS >= '1990') OR (ELCODE = 'ABNKC12060' AND LASTOBS >= '1980')) OR (((ELCODE LIKE 'P%' OR ELCODE LIKE 'N%' OR ELCODE LIKE 'C%' OR ELCODE LIKE 'H%' OR ELCODE LIKE 'G%') AND (LASTOBS >= '1967')) OR ((ELCODE LIKE 'P%' OR ELCODE LIKE 'N%') AND (USESA = 'LE' OR USESA = 'LT') AND (LASTOBS >= '1950'))) OR (((ELCODE LIKE 'AF%' OR ELCODE LIKE 'AA%' OR ELCODE LIKE 'AR%') AND (LASTOBS >= '1950')) OR (ELCODE = 'ARADE03011')) OR (((ELCODE LIKE 'AM%' OR ELCODE LIKE 'OBAT%') AND ELCODE <> 'AMACC01150' AND LASTOBS >= '1970') OR (ELCODE = 'AMACC01100' AND LASTOBS >= '1950') OR (ELCODE = 'AMACC01150' AND LASTOBS >= '1985')) OR (((ELCODE LIKE 'IC%' OR ELCODE LIKE 'IIEPH%' OR ELCODE LIKE 'IITRI%' OR ELCODE LIKE 'IMBIV%' OR ELCODE LIKE 'IMGAS%' OR ELCODE LIKE 'IP%' OR ELCODE LIKE 'IZ%') AND LASTOBS >= '1950') OR (ELCODE LIKE 'I%' AND ELCODE NOT LIKE 'IC%' AND ELCODE NOT LIKE 'IIEPH%' AND ELCODE NOT LIKE 'IITRI%' AND ELCODE NOT LIKE 'IMBIV%' AND ELCODE NOT LIKE 'IMGAS%' AND ELCODE NOT LIKE 'IP%' AND ELCODE NOT LIKE 'IZ%' AND LASTOBS >= '1980'))OR (LASTOBS = '' OR LASTOBS = ' ')) AND (EO_TRACK = 'Y' OR EO_TRACK = 'W') AND (LASTOBS <> 'NO DATE' AND EORANK <> 'X' AND EORANK <> 'X?') AND (LU_exclude = 'N' OR LU_exclude IS NULL)")
spec_id_tbl = arcpy.TableToTable_conversion(spec_id_tbl, 'in_memory', 'spec_id_tbl')
arcpy.JoinField_management(cpp_eo_ptreps, 'ELSUBID', spec_id_tbl, 'ElSubID', ['specid', 'specid_2', 'specid_3'])

fields = arcpy.ListFields(cpp_eo_ptreps)
keepFields = ['OBJECTID', 'Shape', 'EO_ID', 'EO_TYPE', 'EO_TRACK', 'ER_RULE', 'EO_RULE', 'specid', 'specid_2', 'specid_3']
dropFields = [x.name for x in fields if x.name not in keepFields]
arcpy.DeleteField_management(cpp_eo_ptreps, dropFields)


#arcpy.SelectLayerByAttribute_management(in_layer_or_view="ptreps", selection_type="NEW_SELECTION",
#where_clause="(((ELCODE LIKE 'AB%' AND LASTOBS >= '1990') OR (ELCODE = 'ABNKC12060' AND LASTOBS >= '1980')) OR (((ELCODE LIKE 'P%' OR ELCODE LIKE 'N%' OR ELCODE LIKE 'C%' OR ELCODE LIKE 'H%' OR ELCODE LIKE 'G%') AND (LASTOBS >= '1967')) OR ((ELCODE LIKE 'P%' OR ELCODE LIKE 'N%') AND (USESA = 'LE' OR USESA = 'LT') AND (LASTOBS >= '1950'))) OR (((ELCODE LIKE 'AF%' OR ELCODE LIKE 'AA%' OR ELCODE LIKE 'AR%') AND (LASTOBS >= '1950')) OR (ELCODE = 'ARADE03011')) OR (((ELCODE LIKE 'AM%' OR ELCODE LIKE 'OBAT%') AND ELCODE <> 'AMACC01150' AND LASTOBS >= '1970') OR (ELCODE = 'AMACC01100' AND LASTOBS >= '1950') OR (ELCODE = 'AMACC01150' AND LASTOBS >= '1985')) OR (((ELCODE LIKE 'IC%' OR ELCODE LIKE 'IIEPH%' OR ELCODE LIKE 'IITRI%' OR ELCODE LIKE 'IMBIV%' OR ELCODE LIKE 'IMGAS%' OR ELCODE LIKE 'IP%' OR ELCODE LIKE 'IZ%') AND LASTOBS >= '1950') OR (ELCODE LIKE 'I%' AND ELCODE NOT LIKE 'IC%' AND ELCODE NOT LIKE 'IIEPH%' AND ELCODE NOT LIKE 'IITRI%' AND ELCODE NOT LIKE 'IMBIV%' AND ELCODE NOT LIKE 'IMGAS%' AND ELCODE NOT LIKE 'IP%' AND ELCODE NOT LIKE 'IZ%' AND LASTOBS >= '1980'))OR (LASTOBS = '' OR LASTOBS = ' ')) AND (EO_TRACK = 'Y' OR EO_TRACK = 'W') AND (LASTOBS <> 'NO DATE' AND EORANK <> 'X' AND EORANK <> 'X?') AND (LU_exclude = 'N' OR LU_exclude IS NULL)")


