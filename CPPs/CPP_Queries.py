#-------------------------------------------------------------------------------
# Name:        CPP Query for Qualifying EOs
# Purpose:
# Author:      Molly Moore
# Created:     2017
# Updated:     2020-11-25
#-------------------------------------------------------------------------------

#import packages
import arcpy, time, datetime, os
from datetime import datetime
import sqlite3
import pyodbc

#set start time
start_time = time.time()

#establish environment settings
arcpy.env.workspace = r'in_memory'
arcpy.env.overwriteOutput = True

#set paths
cpp_db = r'W:\\Heritage\\Heritage_Data\\CPP\\CPP_Specs\\CPP_SpecID.sqlite'
BioticsGDB = r'W:\Heritage\Heritage_Data\Biotics_datasets.gdb'
outPath = r'W:\\Heritage\\Heritage_Data\\CPP\\CPP_EOReps\\CPP_EOReps.gdb'
reportPath = r'W:\\Heritage\\Heritage_Data\\CPP\\CPP_EOReps'
accessdb = r'P:\Conservation Programs\Natural Heritage Program\Data Management\ACCESS databases\Processing_database\DM_processing.accdb'
scratch = r'H:\temp\temp.gdb'

date1 = raw_input("Enter the date after which you want to include records (MM/DD/YYYY)")
date2 = raw_input("Enter the date before which you want to include records (MM/DD/YYYY)")

#connect to cpp sqlite database to create spec id dictionary
conn = sqlite3.connect(cpp_db)
cur = conn.cursor()
cur.execute("SELECT * FROM SpecID_Table")
specid_dict = {}
for row in cur.fetchall():
    specid_dict[row[0]] = row[1:]

#connect to Biotics GDB to get source feature datasets
eo_ptreps = os.path.join(BioticsGDB, 'eo_ptreps')
srcfeatures = ['eo_sourceln', 'eo_sourcept', 'eo_sourcepy']
sfs = ['line', 'point', 'poly']

#convert sf datasets to tables and merge together
for srcfeature, sf in zip(srcfeatures, sfs):
    fc = os.path.join(BioticsGDB, srcfeature)
    sf = arcpy.TableToTable_conversion(fc, scratch, sf)
sf = arcpy.Merge_management(sfs, os.path.join(scratch, 'sf'))

#query merged sf table to find records with high locational uncertainty
lu_query = "(LU_DIST >= 2500 AND LU_UNIT = 'METERS') OR (LU_DIST >= 1.553428 AND LU_UNIT = 'MILES') OR (LU_DIST >= 8202.1 AND LU_UNIT = 'FEET')"
sf_lu = arcpy.TableToTable_conversion(sf, scratch, 'sf_lu', lu_query)

#find SF count per EO
sf_count = arcpy.Statistics_analysis(sf, os.path.join(scratch, 'sf_count'), 'EO_ID COUNT', 'EO_ID')
#find SF count per EO with high locational uncertainty
sf_lu_count = arcpy.Statistics_analysis(sf_lu, os.path.join(scratch, 'sf_lu_count'), 'EO_ID COUNT', 'EO_ID')
#join SF count per EO and SF count per EO with high locational uncertainty
arcpy.JoinField_management(sf_lu_count, 'EO_ID', sf_count, 'EO_ID', 'COUNT_EO_ID')

#add LU_exclude field and fill with Y if SF count per EO is equal to SF count per EO with high locational uncertainty
arcpy.AddField_management(sf_lu_count, 'LU_exclude', 'TEXT', '', '', 1)
with arcpy.da.UpdateCursor(sf_lu_count, ['COUNT_EO_ID', 'COUNT_EO_ID_1', 'LU_exclude']) as cursor:
    for row in cursor:
        if row[0] == row[1]:
            row[2] = 'Y'
        else:
            row[2] = 'N'
        cursor.updateRow(row)

#create table from EO pt rep layer and join LU_exclude field
ptreps = arcpy.TableToTable_conversion(eo_ptreps, scratch, 'ptreps')
arcpy.JoinField_management(ptreps, 'EO_ID', sf_lu_count, 'EO_ID', 'LU_exclude')

#calculate 50 years ago to use with state listed plants
year = datetime.now().year - 50
#calculate date for use in filename
date = datetime.today().strftime("%Y%m%d")

#use query to copy all qualifying EO records to new table
where_clause = "(((ELCODE LIKE 'AB%' AND LASTOBS >= '1990') OR (ELCODE = 'ABNKC12060' AND LASTOBS >= '1980')) OR (((ELCODE LIKE 'P%' OR ELCODE LIKE 'N%' OR ELCODE LIKE 'C%' OR ELCODE LIKE 'H%' OR ELCODE LIKE 'G%') AND (LASTOBS >= '{0}')) OR ((ELCODE LIKE 'P%' OR ELCODE LIKE 'N%') AND (USESA = 'LE' OR USESA = 'LT') AND (LASTOBS >= '1950'))) OR (((ELCODE LIKE 'AF%' OR ELCODE LIKE 'AA%' OR ELCODE LIKE 'AR%') AND (LASTOBS >= '1950')) OR (ELCODE = 'ARADE03011')) OR (((ELCODE LIKE 'AM%' OR ELCODE LIKE 'OBAT%') AND ELCODE <> 'AMACC01150' AND LASTOBS >= '1970') OR (ELCODE = 'AMACC01100' AND LASTOBS >= '1950') OR (ELCODE = 'AMACC01150' AND LASTOBS >= '1985')) OR (((ELCODE LIKE 'IC%' OR ELCODE LIKE 'IIEPH%' OR ELCODE LIKE 'IITRI%' OR ELCODE LIKE 'IMBIV%' OR ELCODE LIKE 'IMGAS%' OR ELCODE LIKE 'IP%' OR ELCODE LIKE 'IZ%') AND LASTOBS >= '1950') OR (ELCODE LIKE 'I%' AND ELCODE NOT LIKE 'IC%' AND ELCODE NOT LIKE 'IIEPH%' AND ELCODE NOT LIKE 'IITRI%' AND ELCODE NOT LIKE 'IMBIV%' AND ELCODE NOT LIKE 'IMGAS%' AND ELCODE NOT LIKE 'IP%' AND ELCODE NOT LIKE 'IZ%' AND LASTOBS >= '1980'))OR (LASTOBS = '' OR LASTOBS = ' ')) AND (EO_TRACK = 'Y' OR EO_TRACK = 'W') AND (LASTOBS <> 'NO DATE' AND EORANK <> 'X' AND EORANK <> 'X?') AND (LU_exclude = 'N' OR LU_exclude IS NULL)".format(year)
cpp_eo_ptreps = arcpy.TableToTable_conversion(ptreps, scratch, 'cpp_eo_ptreps_'+date, where_clause)

#add spec id fields
f_name = ["specid","specid_2","specid_3","specid_comments"]
f_length = [75,75,75,500]
for n,l in zip(f_name,f_length):
    arcpy.AddField_management(cpp_eo_ptreps,n,"TEXT","","",l)

#use spec id dictionary to fill spec id fields
with arcpy.da.UpdateCursor(cpp_eo_ptreps,["ELSUBID","specid","specid_2","specid_3","specid_comments"]) as cursor:
    for row in cursor:
        for k,v in specid_dict.items():
            if str(k)==str(int(row[0])):
                row[1]=v[0]
                row[2]=v[1]
                row[3]=v[2]
                row[4]=v[3]
                cursor.updateRow(row)

#delete unneeded fields
oid_field = arcpy.Describe(cpp_eo_ptreps).OIDFieldName
keepFields = [oid_field, 'Shape', 'EO_ID', 'SNAME', 'SCOMNAME', 'ELSUBID', 'EO_TYPE', 'EO_TRACK', 'ER_RULE', 'EO_RULE', 'specid', 'specid_2', 'specid_3', 'specid_comments']
fields = arcpy.ListFields(cpp_eo_ptreps)
dropFields = [x.name for x in fields if x.name not in keepFields]
arcpy.DeleteField_management(cpp_eo_ptreps, dropFields)

#copy final table to output location
arcpy.TableToTable_conversion(cpp_eo_ptreps, outPath, 'cpp_qualify_EO_'+date)

#add processing DB fields to cpp_eo_ptreps layer in ArcMap
f_name = ["date_created","mapper_status","description"]
f_length = ["",12,500]
f_type = ["DATE","TEXT","TEXT"]
for n,t,l in zip(f_name,f_type,f_length):
    arcpy.AddField_management(cpp_eo_ptreps,n,t,"","",l)

#connect to the processing DB and get records from EO log that meet date criteria
print("Connecting to processing DB")
conn = pyodbc.connect('Driver={Microsoft Access Driver (*.mdb, *.accdb)};DBQ='+accessdb+r';')
cursor = conn.cursor()
cursor.execute("SELECT EOID, [Date created, updated or deleted], [Mapper - new, update, or deletion], [Brief description] FROM [EO log] WHERE EOID IS NOT NULL AND [Mapper - new, update, or deletion] <> 'NA' AND [Date created, updated or deleted] >= #{0}# AND [Date created, updated or deleted] <= #{1}#".format(date1, date2))
print("The following records were fetched:")
for row in cursor.fetchall():
    print(row)

#create dictionary with fetched records
eolog_dict = {}
for row in cursor.fetchall():
    eolog_dict[row[0]] = row[1:]

#create list of EOIDs in cpp_eo_ptreps layer
with arcpy.da.SearchCursor(cpp_eo_ptreps,"EO_ID") as cursor:
    qualified_eos = sorted({row[0] for row in cursor})

#if EO qualifies for CPP, fill with EO log information. Otherwise, delete record.
with arcpy.da.UpdateCursor(cpp_eo_ptreps,["EO_ID","date_created","mapper_status","description"]) as cursor:
    for row in cursor:
        for k,v in eolog_dict.items():
            if int(k) in qualified_eos:
                if str(k)==str(int(row[0])):
                    row[1]=v[0]
                    row[2]=v[1]
                    row[3]=v[2]
                    cursor.updateRow(row)
            else:
                cursor.deleteRow()

#delete records that are not in EO log records
eolog_list = list(eolog_dict.keys())
with arcpy.da.UpdateCursor(cpp_eo_ptreps,"EO_ID") as cursor:
    for row in cursor:
        if row[0] in eolog_list:
            pass
        else:
            cursor.deleteRow()

#create Excel spreadsheet of returned records
arcpy.TableToExcel_conversion(cpp_eo_ptreps,os.path.join(reportPath, 'CPP_EO_Changes_'+date1.replace("/","")+"_"+date2.replace("/","")+".xls"))

#report time
Time = "The script took {} minutes to run.".format(str((time.time()-start_time)/60))
print(Time)
