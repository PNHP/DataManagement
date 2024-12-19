# -------------------------------------------------------------------------------
# Name:        CPP Outstanding
# Purpose:     Queries for Outstanding EOs that need CPPs
# Author:      Molly Moore
# Created:     2022-05-18
# -------------------------------------------------------------------------------

eo_log_path = "csv"
# eo_log_path = "access"

# import packages
import arcpy
import os
from datetime import datetime
import sqlite3
import pyodbc
import pandas as pd
import csv

# set start time
start_time = time.time()

# establish environment settings
arcpy.env.workspace = r'H:\\temp\temp.gdb'
arcpy.env.overwriteOutput = True

# set paths
cpp_db = r'W:\\Heritage\\Heritage_Data\\CPP\\CPP_Specs\\CPP_SpecID.sqlite'
BioticsGDB = r'W:\Heritage\Heritage_Data\Biotics_datasets.gdb'
outPath = r'W:\\Heritage\\Heritage_Data\\CPP\\CPP_EOReps\\CPP_EOReps.gdb'
reportPath = r'W:\\Heritage\\Heritage_Data\\CPP\\CPP_EOReps'
if eo_log_path == "csv":
    accessdb = r'H:\temp\EO log.csv' # enter path to exported EO Log .csv file
else:
    accessdb = r'P:\Conservation Programs\Natural Heritage Program\Data Management\ACCESS databases\Processing_database\DM_processing.accdb'
scratch = r'H:\temp\temp.gdb'

cpp_core = r'C:\\Users\\MMoore\\AppData\\Roaming\\Esri\\ArcGISPro\\Favorites\\PNHP_Working_pgh-gis1.sde\\DBO.CPPConservationPlanningPolygons\\DBO.CPP_Core'
cpp_supporting = r'C:\\Users\\MMoore\\AppData\\Roaming\\Esri\\ArcGISPro\\Favorites\\PNHP_Working_pgh-gis1.sde\\DBO.CPPConservationPlanningPolygons\\DBO.CPP_Supporting'

# connect to cpp sqlite database to create spec id dictionary
conn = sqlite3.connect(cpp_db)
cur = conn.cursor()
cur.execute("SELECT * FROM SpecID_Table")
specid_dict = {}
for row in cur.fetchall():
    specid_dict[row[0]] = row[1:]

# connect to Biotics GDB to get source feature datasets
eo_ptreps = os.path.join(BioticsGDB, 'eo_ptreps')
srcfeatures = ['eo_sourceln', 'eo_sourcept', 'eo_sourcepy']
sfs = ['line', 'point', 'poly']

# convert sf datasets to tables and merge together
print("converting SF datasets and merging together")
for srcfeature, sf in zip(srcfeatures, sfs):
    fc = os.path.join(BioticsGDB, srcfeature)
    sf = arcpy.TableToTable_conversion(fc, scratch, sf)
sf = arcpy.Merge_management(sfs, os.path.join(scratch, 'sf'))

# query merged sf table to find records with high locational uncertainty
lu_query = "(LU_DIST >= 2500 AND LU_UNIT = 'METERS') OR (LU_DIST >= 1.553428 AND LU_UNIT = 'MILES') OR (LU_DIST >= 8202.1 AND LU_UNIT = 'FEET')"
sf_lu = arcpy.TableToTable_conversion(sf, scratch, 'sf_lu', lu_query)

print("finding SF counts")
# find SF count per EO
sf_count = arcpy.Statistics_analysis(sf, os.path.join(scratch, 'sf_count'), 'EO_ID COUNT', 'EO_ID')
# find SF count per EO with high locational uncertainty
sf_lu_count = arcpy.Statistics_analysis(sf_lu, os.path.join(scratch, 'sf_lu_count'), 'EO_ID COUNT', 'EO_ID')
# join SF count per EO and SF count per EO with high locational uncertainty
arcpy.JoinField_management(sf_lu_count, 'EO_ID', sf_count, 'EO_ID', 'COUNT_EO_ID')

# add LU_exclude field and fill with Y if SF count per EO is equal to SF count per EO with high locational uncertainty
arcpy.AddField_management(sf_lu_count, 'LU_exclude', 'TEXT', '', '', 1)
with arcpy.da.UpdateCursor(sf_lu_count, ['COUNT_EO_ID', 'COUNT_EO_ID_1', 'LU_exclude']) as cursor:
    for row in cursor:
        if row[0] == row[1]:
            row[2] = 'Y'
        else:
            row[2] = 'N'
        cursor.updateRow(row)

# create table from EO pt rep layer and join LU_exclude field
ptreps = arcpy.TableToTable_conversion(eo_ptreps, scratch, 'ptreps')
arcpy.JoinField_management(ptreps, 'EO_ID', sf_lu_count, 'EO_ID', 'LU_exclude')

# calculate 50 years ago to use with state listed plants
year = datetime.now().year - 50
# calculate date for use in filename
date = datetime.today().strftime("%Y%m%d")

print("create CPP EOptreps layer")
# use query to copy all qualifying EO records to new table
where_clause = "(((ELCODE LIKE 'AB%' AND LASTOBS >= '1990') OR (ELCODE = 'ABNKC12060' AND LASTOBS >= '1980')) OR (((ELCODE LIKE 'P%' OR ELCODE LIKE 'N%' OR ELCODE LIKE 'C%' OR ELCODE LIKE 'H%' OR ELCODE LIKE 'G%') AND (LASTOBS >= '{0}')) OR ((ELCODE LIKE 'P%' OR ELCODE LIKE 'N%') AND (USESA = 'LE' OR USESA = 'LT') AND (LASTOBS >= '1950'))) OR (((ELCODE LIKE 'AF%' OR ELCODE LIKE 'AA%' OR ELCODE LIKE 'AR%') AND (LASTOBS >= '1950')) OR (ELCODE = 'ARADE03011')) OR (((ELCODE LIKE 'AM%' OR ELCODE LIKE 'OBAT%') AND ELCODE <> 'AMACC01150' AND LASTOBS >= '1970') OR (ELCODE = 'AMACC01100' AND LASTOBS >= '1950') OR (ELCODE = 'AMACC01150' AND LASTOBS >= '1985')) OR (((ELCODE LIKE 'IC%' OR ELCODE LIKE 'IIEPH%' OR ELCODE LIKE 'IITRI%' OR ELCODE LIKE 'IMBIV%' OR ELCODE LIKE 'IMGAS%' OR ELCODE LIKE 'IP%' OR ELCODE LIKE 'IZ%') AND LASTOBS >= '1950') OR (ELCODE LIKE 'I%' AND ELCODE NOT LIKE 'IC%' AND ELCODE NOT LIKE 'IIEPH%' AND ELCODE NOT LIKE 'IITRI%' AND ELCODE NOT LIKE 'IMBIV%' AND ELCODE NOT LIKE 'IMGAS%' AND ELCODE NOT LIKE 'IP%' AND ELCODE NOT LIKE 'IZ%' AND LASTOBS >= '1980'))OR (LASTOBS = '' OR LASTOBS = ' ')) AND (EO_TRACK = 'Y' OR EO_TRACK = 'W') AND (LASTOBS <> 'NO DATE' AND EORANK <> 'X' AND EORANK <> 'X?' AND EST_RA <> 'Very Low' AND EST_RA <> 'Low') AND (LU_exclude = 'N' OR LU_exclude IS NULL)".format(
    year)
cpp_eo_ptreps = arcpy.TableToTable_conversion(ptreps, scratch, 'cpp_eo_ptreps_' + date, where_clause)

# add spec id fields
f_name = ["specid", "specid_2", "specid_3", "specid_comments"]
f_length = [75, 75, 75, 500]
for n, l in zip(f_name, f_length):
    arcpy.AddField_management(cpp_eo_ptreps, n, "TEXT", "", "", l)

# use spec id dictionary to fill spec id fields
with arcpy.da.UpdateCursor(cpp_eo_ptreps, ["ELSUBID", "specid", "specid_2", "specid_3", "specid_comments"]) as cursor:
    for row in cursor:
        for k, v in specid_dict.items():
            if str(k) == str(int(row[0])):
                row[1] = v[0]
                row[2] = v[1]
                row[3] = v[2]
                row[4] = v[3]
                cursor.updateRow(row)

# add processing DB fields to cpp_eo_ptreps layer in ArcMap
f_name = ["core", "supporting"]
for name in f_name:
    arcpy.AddField_management(cpp_eo_ptreps, name, "TEXT", "", "", 25)

print("create core/supporting dictionaries")
core_dict = {}
with arcpy.da.SearchCursor(cpp_core, ["EO_ID", "BioticsExportDate"]) as cursor:
    for row in cursor:
        core_dict[row[0]] = [row[1]]

supporting_dict = {}
with arcpy.da.SearchCursor(cpp_supporting, ["EO_ID", "BioticsExportDate"]) as cursor:
    for row in cursor:
        supporting_dict[row[0]] = [row[1]]

print("create eo log dataframe and delete extras")


if eo_log_path == "access":
    #connect to the processing DB and get ALL records from processing DB
    print("Connecting to processing DB")
    conn = pyodbc.connect('Driver={Microsoft Access Driver (*.mdb, *.accdb)};DBQ='+accessdb+r';')
    cursor = conn.cursor()
    cursor.execute("SELECT EOID, [Date created, updated or deleted], [Mapper - new, update, or deletion], [Brief description], County FROM [EO log] WHERE EOID IS NOT NULL AND [Mapper - new, update, or deletion] <> 'NA'")
    records = cursor.fetchall()
    eolog = pd.DataFrame.from_records(records, columns=["EO_ID", "Date_Updated", "Mapper_Desc", "Desc", "County"])

elif eo_log_path == "csv":
    print("Connecting to .csv export")
    # read in .csv eo log file to Pandas dataframe with Latin-1 encoding to deal with weird characters
    eolog = pd.read_csv(accessdb, sep=',', encoding="Latin-1", low_memory=False)
    # filter out records that have Null EOIDs and that don't have map updates
    eolog = eolog.query('EOID.notna() and `Mapper - new, update, or deletion`.notna()')
    # convert date field to datetime from string
    eolog.loc[:,'Date created, updated or deleted'] = pd.to_datetime(eolog.loc[:,'Date created, updated or deleted'])

    # keep only needed columns
    eolog = eolog[['EOID', 'Date created, updated or deleted', 'Mapper - new, update, or deletion', 'Brief description', 'County']]
    # convert EOID field to integer from float
    eolog['EOID'] = eolog['EOID'].astype('Int64')
else:
    print("there is some issue with the EO Log input type")

eolog = eolog.sort_values(by='Date created, updated or deleted', ascending=False).drop_duplicates(subset="EOID", keep='first')

eolog_dict = {}
for index, row in eolog.iterrows():
    eolog_dict[row['EOID']] = [row['Date created, updated or deleted'], row['Mapper - new, update, or deletion']]

print("create eo log update lists")
core_update_list = []
for k1, v1 in eolog_dict.items():
    for k, v in core_dict.items():
        if k is not None and v[0] is not None and k1 is not None and v1[0] is not None:
            if k1 == k and v1[0] > v[0]:
                core_update_list.append(k1)

supporting_update_list = []
for k1, v1 in eolog_dict.items():
    for k, v in supporting_dict.items():
        if k is not None and v[0] is not None and k1 is not None and v1[0] is not None:
            if k1 == k and v1[0] > v[0]:
                supporting_update_list.append(k1)

print("update core/supporting fields")
with arcpy.da.UpdateCursor(cpp_eo_ptreps, ["EO_ID", "core", "supporting"]) as cursor:
    for row in cursor:
        if row[0] not in core_dict.keys():
            row[1] = "create"
            cursor.updateRow(row)
        elif row[0] in core_update_list:
            row[1] = "update"
            cursor.updateRow(row)
        else:
            pass
        if row[0] not in supporting_dict.keys():
            row[2] = "create"
            cursor.updateRow(row)
        elif row[0] in supporting_update_list:
            row[2] = "update"
            cursor.updateRow(row)
        else:
            pass

with arcpy.da.UpdateCursor(cpp_eo_ptreps, ["core", "supporting"]) as cursor:
    for row in cursor:
        if row[0] is None and row[1] is None:
            cursor.deleteRow()

print("create final dict and write csv")
final_dict = {}
with arcpy.da.SearchCursor(cpp_eo_ptreps,
                           ['EO_ID', "core", "supporting", 'SNAME', 'SCOMNAME', 'specid', 'specid_2', 'specid_3',
                            'specid_comments', 'ER_RULE', 'EO_TRACK', 'ELSUBID', 'EO_TYPE']) as cursor:
    for row in cursor:
        final_dict[row[0]] = [row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11],
                              row[12]]

with open(os.path.join(reportPath, 'CPP_Outstanding_' + date + '.csv'), 'w', newline='') as csvfile:
    csv_output = csv.writer(csvfile)
    csv_output.writerow(
        ['EO_ID', 'Core Status', 'Supporting Status', 'SNAME', 'SCOMNAME', 'specid', 'specid_2', 'specid_3',
         'specid_comments', 'ER_RULE', 'EO_TRACK', 'ELSUBID', 'EO_TYPE'])
    for key in sorted(final_dict.keys()):
        csv_output.writerow([key] + final_dict[key])

# report time
Time = "The script took {} minutes to run.".format(str((time.time() - start_time) / 60))
print(Time)
