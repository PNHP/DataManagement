# -------------------------------------------------------------------------------
# Name:        CPP Query for Qualifying EOs
# Purpose:
# Author:      Molly Moore
# Created:     2017
# Updates:
# 2023-11-08 - updated to enable capability to use manual .csv export of the EO Log from the Access processing database
# so that it can work if WPC Apps is down.
# -------------------------------------------------------------------------------

#### NOTE: IF RUNNING WITH THE ACCESS OPTION, THIS NEEDS TO RUN ON A COMPUTER WITH MS ACCESS DRIVERS INSTALLED TO ACCESS
#### PROCESSING DB WITH PYODBC. THIS CAN RUN ON WPC APPS WITH PYSCRIPTER OR IDLE.

#### NOTE: IF RUNNING WITH THE CSV OPTION, THE USER MUST FIRST EXPORT A CSV OF THE EO LOG AND UPDATE THE PATH TO THE
#### EXPORTED EO LOG.

#### USER MUST SET DATE RANGE BELOW!!!!!!!!!!!!
date1 = "06/27/2024"
date2 = "10/24/2024"

# eo_log_path = "access" # this option needs to run on a computer with MS Access Drivers installed to access processing DB with PYODBC
eo_log_path = "csv" # for this option, you need to manually export a .csv of the EO Log from the Processing Access database and update the path below
if eo_log_path == "csv":
    accessdb = r'H:\temp\EO log.csv' # enter path to exported EO Log .csv file

# import packages
import arcpy
import os
from datetime import datetime
import sqlite3
import pyodbc
import csv
import pandas as pd

# set start time - this isn't really important except to report about how long the script took
start_time = time.time()

# establish environment settings
arcpy.env.workspace = r'memory'
arcpy.env.overwriteOutput = True

# set paths to datasets and out folders - these shouldn't need to change unless there are major restructures on the W: drive
cpp_db = r'W:\\Heritage\\Heritage_Data\\CPP\\CPP_Specs\\CPP_SpecID.sqlite'
BioticsGDB = r'W:\Heritage\Heritage_Data\Biotics_datasets.gdb'
outPath = r'W:\\Heritage\\Heritage_Data\\CPP\\CPP_EOReps\\CPP_EOReps.gdb'
reportPath = r'W:\\Heritage\\Heritage_Data\\CPP\\CPP_EOReps'
if eo_log_path == "access":
    accessdb = r'P:\Conservation Programs\Natural Heritage Program\Data Management\ACCESS databases\Processing_database\DM_processing.accdb'
scratch = r'memory'

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

########################################################################################################################
### THIS SECTION IS TO FIGURE OUT IF ALL SOURCE FEATURES IN AN EO HAVE HIGH LOCATIONAL UNCERTAINTY AND, IF SO, EXCLUDE
### EOs THAT ONLY HAVE SOURCE FEATURES WITH HIGH LOCATIONAL UNCERTAINTY.
########################################################################################################################

# convert sf datasets to tables and merge together
for srcfeature, sf in zip(srcfeatures, sfs):
    fc = os.path.join(BioticsGDB, srcfeature)
    sf = arcpy.TableToTable_conversion(fc, scratch, sf)
sf = arcpy.Merge_management(sfs, os.path.join(scratch, 'sf'))

# query merged sf table to find records with high locational uncertainty
lu_query = "(LU_DIST >= 2500 AND LU_UNIT = 'METERS') OR (LU_DIST >= 1.553428 AND LU_UNIT = 'MILES') OR (LU_DIST >= 8202.1 AND LU_UNIT = 'FEET')"
sf_lu = arcpy.TableToTable_conversion(sf, scratch, 'sf_lu', lu_query)

# find number of source features per EO
sf_count = arcpy.Statistics_analysis(sf, os.path.join(scratch, 'sf_count'), 'EO_ID COUNT', 'EO_ID')
# find number of source features with high locational uncertainty per EO
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

########################################################################################################################
## End LU Exclude Section
########################################################################################################################

# create table from EO pt rep layer and join LU_exclude field
ptreps = arcpy.TableToTable_conversion(eo_ptreps, scratch, 'ptreps')
arcpy.JoinField_management(ptreps, 'EO_ID', sf_lu_count, 'EO_ID', 'LU_exclude')

# calculate 50 years ago to use as date cutoff for state listed plants
year = datetime.now().year - 50
# calculate date for use in cpp_eo_ptreps output filename
date = datetime.today().strftime("%Y%m%d")

# use query to copy all qualifying EO records to new table - criteria for inclusion can be found in the CPP documentation on the W: drive (W:\Heritage\Heritage_Data\CPP\Documentation)
where_clause = "(((ELCODE LIKE 'AB%' AND LASTOBS >= '1990') OR (ELCODE = 'ABNKC12060' AND LASTOBS >= '1980')) OR (((ELCODE LIKE 'P%' OR ELCODE LIKE 'N%' OR ELCODE LIKE 'C%' OR ELCODE LIKE 'H%' OR ELCODE LIKE 'G%') AND (LASTOBS >= '{0}')) OR ((ELCODE LIKE 'P%' OR ELCODE LIKE 'N%') AND (USESA = 'LE' OR USESA = 'LT') AND (LASTOBS >= '1950'))) OR (((ELCODE LIKE 'AF%' OR ELCODE LIKE 'AA%' OR ELCODE LIKE 'AR%') AND (LASTOBS >= '1950')) OR (ELCODE = 'ARADE03011')) OR (((ELCODE LIKE 'AM%' OR ELCODE LIKE 'OBAT%') AND ELCODE <> 'AMACC01150' AND LASTOBS >= '1970') OR (ELCODE = 'AMACC01100' AND LASTOBS >= '1950') OR (ELCODE = 'AMACC01150' AND LASTOBS >= '1985')) OR (((ELCODE LIKE 'IC%' OR ELCODE LIKE 'IIEPH%' OR ELCODE LIKE 'IITRI%' OR ELCODE LIKE 'IMBIV%' OR ELCODE LIKE 'IMGAS%' OR ELCODE LIKE 'IP%' OR ELCODE LIKE 'IZ%') AND LASTOBS >= '1950') OR (ELCODE LIKE 'I%' AND ELCODE NOT LIKE 'IC%' AND ELCODE NOT LIKE 'IIEPH%' AND ELCODE NOT LIKE 'IITRI%' AND ELCODE NOT LIKE 'IMBIV%' AND ELCODE NOT LIKE 'IMGAS%' AND ELCODE NOT LIKE 'IP%' AND ELCODE NOT LIKE 'IZ%' AND LASTOBS >= '1980'))OR (LASTOBS = '' OR LASTOBS = ' ')) AND (EO_TRACK = 'Y' OR EO_TRACK = 'W') AND (LASTOBS <> 'NO DATE' AND EORANK <> 'X' AND EORANK <> 'X?') AND (LU_exclude = 'N' OR LU_exclude IS NULL)".format(year)
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

# delete unneeded fields
oid_field = arcpy.Describe(cpp_eo_ptreps).OIDFieldName
keepFields = [oid_field, 'Shape', 'EO_ID', 'SNAME', 'SCOMNAME', 'ELSUBID', 'EO_TYPE', 'EO_TRACK', 'ER_RULE', 'EO_RULE', 'specid', 'specid_2', 'specid_3', 'specid_comments']
fields = arcpy.ListFields(cpp_eo_ptreps)
dropFields = [x.name for x in fields if x.name not in keepFields]
arcpy.DeleteField_management(cpp_eo_ptreps, dropFields)

# copy final table to output location
arcpy.TableToTable_conversion(cpp_eo_ptreps, outPath, 'cpp_qualify_EO_' + date)

# add processing DB fields to cpp_eo_ptreps layer in ArcMap
f_name = ["date_created", "mapper_status", "description", "county"]
f_length = ["", 25, 500, 75]
f_type = ["DATE", "TEXT", "TEXT", "TEXT"]
for n, t, l in zip(f_name, f_type, f_length):
    arcpy.AddField_management(cpp_eo_ptreps, n, t, "", "", l)

if eo_log_path == "access":
    # connect to the processing DB and get records from EO log that meet date criteria
    print("Connecting to processing DB")
    conn = pyodbc.connect('Driver={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=' + accessdb + r';')
    cursor = conn.cursor()
    # filter out records that have null EOIDs, null Mapper status, and that are not between the interested date range
    cursor.execute("SELECT EOID, [Date created, updated or deleted], [Mapper - new, update, or deletion], [Brief description], County FROM [EO log] WHERE EOID IS NOT NULL AND [Mapper - new, update, or deletion] <> 'NA' AND [Date created, updated or deleted] >= #{0}# AND [Date created, updated or deleted] <= #{1}#".format(date1, date2))
    records = cursor.fetchall()

    # create dictionary with fetched records
    eolog_dict = {}
    for row in records:
        eolog_dict[row[0]] = row[1:]

elif eo_log_path == "csv":
    print("Connecting to .csv export")
    # read in .csv eo log file to Pandas dataframe with Latin-1 encoding to deal with weird characters
    eo_log = pd.read_csv(accessdb, sep=',', encoding="Latin-1", low_memory=False)
    # filter out records that have Null EOIDs and that don't have map updates
    eo_log = eo_log.query('EOID.notna() and `Mapper - new, update, or deletion`.notna()')
    # convert cutoff dates to datetime format
    start_day = pd.to_datetime(date1)
    end_day = pd.to_datetime(date2)
    # convert date field to datetime from string
    eo_log.loc[:,'Date created, updated or deleted'] = pd.to_datetime(eo_log.loc[:,'Date created, updated or deleted'])
    # filter out records between date cutoffs
    eo_log = eo_log[eo_log['Date created, updated or deleted'].between(start_day, end_day)]

    # keep only needed columns
    eo_log = eo_log[['EOID', 'Date created, updated or deleted', 'Mapper - new, update, or deletion', 'Brief description', 'County']]
    # convert EOID field to integer from float
    eo_log['EOID'] = eo_log['EOID'].astype('Int64')
    # create dictionary from pandas dataframe with EOID as key and other columns as values
    eolog_dict = {k:list(v) for k,v in zip(eo_log['EOID'], eo_log.drop(columns='EOID').values)}
else:
    print("there is some issue with the EO Log input type")

# delete records that are not in EO log records
eolog_list = list(eolog_dict.keys())
with arcpy.da.UpdateCursor(cpp_eo_ptreps, "EO_ID") as cursor:
    for row in cursor:
        if row[0] in eolog_list:
            pass
        else:
            cursor.deleteRow()

# fill cpp_eo_ptreps layer with EO Log information.
with arcpy.da.UpdateCursor(cpp_eo_ptreps, ["EO_ID", "date_created", "mapper_status", "description", "county"]) as cursor:
    for row in cursor:
        for k, v in eolog_dict.items():
            if str(k) == str(int(row[0])):
                row[1] = v[0]
                row[2] = v[1]
                row[3] = v[2]
                row[4] = v[3]
                cursor.updateRow(row)

# get dates for filenames
date1 = datetime.strptime(date1, '%m/%d/%Y').strftime('%Y%m%d')
date2 = datetime.strptime(date2, '%m/%d/%Y').strftime('%Y%m%d')

print("create final dict and write csv")
# create dictionary and fill with final values that will be written to .csv
final_dict = {}
with arcpy.da.SearchCursor(cpp_eo_ptreps,
                           ['EO_ID', 'SNAME', 'SCOMNAME', 'date_created', 'mapper_status', 'description', 'specid',
                            'specid_2', 'specid_3', 'specid_comments', 'ER_RULE', 'EO_TRACK', 'ELSUBID', 'EO_TYPE',
                            'county'], sql_clause=(None, "ORDER BY specid")) as cursor:
    for row in cursor:
        final_dict[row[0]] = [row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12]]

# open new .csv file and write final dictionary to .csv
with open(os.path.join(reportPath, 'CPP_EO_Changes_' + date1 + '_' + date2 + '.csv'), 'w', newline='') as csvfile:
    csv_output = csv.writer(csvfile)
    csv_output.writerow(
        ['EO_ID', 'SNAME', 'SCOMNAME', 'date_created', 'mapper_status', 'description', 'specid', 'specid_2', 'specid_3',
         'specid_comments', 'ER_RULE', 'EO_TRACK', 'ELSUBID', 'EO_TYPE', 'county'])
    for key in sorted(final_dict.keys()):
        csv_output.writerow([key] + final_dict[key])

# report time
Time = "The script took {} minutes to run.".format(str((time.time() - start_time) / 60))
print(Time)
