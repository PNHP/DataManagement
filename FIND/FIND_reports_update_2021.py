#-------------------------------------------------------------------------------
# Name:        FIND Data Management Report Creator
# Purpose:     Pulls current data from FIND enterprise geodatabase and
#              returns Excel spreadsheet containing a summary of data from the
#              requested report.
# Author:      Molly Moore
# Created:     2016-09-06
# Updated:     2016-09-06 - updated to include options for DM Pending and DM
#              Total reports
#              2021-11-09 - cleaned up, added survey status field
#
# To Do List/Future ideas:
# - have script pull from the feature service instead of geodatabase so that
#   everyone can run script
# - include options for other types of reports, such as IDReady, etc.
#
#-------------------------------------------------------------------------------

# import system modules
import arcpy, os, datetime
from arcpy import env
from arcpy.sa import *
import csv

# Set tools to overwrite existing outputs
arcpy.env.overwriteOutput = True
env.workspace = r'in_memory'

################################################################################
# Define global variables and functions to be used throughout toolbox
################################################################################

# file names of the five element feature classes in the FIND enterprise GDB
input_features = ["FIND2021.DBO.el_pt", "FIND2021.DBO.el_line", "FIND2021.DBO.comm_poly", "FIND2021.DBO.comm_pt", "FIND2021.DBO.el_poly", "FIND2021.DBO.survey_poly"]

# file names that are used for temporary output element feature classes
elementShapefiles = ["element_point", "element_line", "community_poly", "community_point", "element_poly", "survey_site"]

# file names that are used for temporary element tables
elementTables = ["element_point1", "element_line1","community_poly1", "community_point1", "element_poly1", "survey_site1"]

# path to FIND enterprise database
elementGDB = r"C:\\Users\\MMoore\\AppData\\Roaming\\Esri\\ArcGISPro\\Favorites\\FIND2021.Working.pgh-gis0.sde"

# path to county layer
counties = r'C:\\Users\\MMoore\\AppData\\Roaming\\Esri\\ArcGISPro\\Favorites\\StateLayers.Default.pgh-gis0.sde\\StateLayers.DBO.Boundaries_Political\\StateLayers.DBO.County'

# path to Biotics ET
et = r"C:\\Users\\MMoore\\AppData\\Roaming\\Esri\\ArcGISPro\\Favorites\\PNHP.Working.pgh-gis0.sde\\PNHP.DBO.ET"

# path to folder where DM reports will be saved as Excel files
ReportsPath = r"P:\Conservation Programs\Natural Heritage Program\Data Management\Instructions, procedures and documentation\FIND\FIND_2021\Reports"

for i, shape_output, table_output in zip(input_features, elementShapefiles, elementTables):
    target_features = os.path.join(elementGDB, i)
    element_features = os.path.join(env.workspace, shape_output)

    # create fieldmap
    fieldmappings = arcpy.FieldMappings()
    fieldmappings.addTable(target_features)
    fieldmappings.addTable(counties)

    # fields to be kept after spatial join
    keepFields = ["COUNTY_NAM", "refcode", "created_user", "created_date", "dm_stat", "dm_stat_comm", "last_up_by",
    "last_up_on", "element_type", "elem_name", "id_prob", "id_prob_comm", "specimen_taken", "specimen_count",
    "specimen_desc", "curatorial_meth", "specimen_repo", "voucher_photo", "elem_found", "archive", "X", "Y"]

    # remove all fields not in keep fields from field map
    for field in fieldmappings.fields:
       if field.name not in keepFields:
           fieldmappings.removeFieldMap(fieldmappings.findFieldMapIndex(field.name))

    # run the spatial join tool
    spatial_join = arcpy.SpatialJoin_analysis(target_features, counties, element_features,field_mapping=fieldmappings)

    arcpy.AddField_management(spatial_join,"element_type","TEXT",field_length = 15,field_alias = "Element Type")

    with arcpy.da.UpdateCursor(spatial_join,"element_type") as cursor:
        for row in cursor:
            row[0] = shape_output
            cursor.updateRow(row)

    arcpy.TableToTable_conversion(shape_output, env.workspace, table_output)

elementRecords = arcpy.Merge_management(elementTables, os.path.join(env.workspace, "elementRecords"))

elementRecords = arcpy.AddField_management(elementRecords,"ELCODE","TEXT","","",15)
elementRecords = arcpy.AddField_management(elementRecords, "Location", "TEXT", "", "", 1)

West = ["ERIE", "CRAWFORD", "MERCER", "LAWRENCE", "BEAVER", "WASHINGTON", "GREENE", "VENANGO", "BUTLER", "ALLEGHENY", "FAYETTE", "WESTMORELAND",
"ARMSTORNG", "INDIANA", "CLARION", "JEFFERSON", "FOREST", "WARREN", "MCKEAN", "ELK", "CLEARFIELD", "CAMBRIA", "SOMERSET", "BEDFORD", "BLAIR",
"CENTRE", "CLINTON", "POTTER", "CAMERON", "HUNTINGDON", "FULTON", "FRANKLIN"]

with arcpy.da.UpdateCursor(elementRecords, ["COUNTY_NAM", "Location"]) as cursor:
    for row in cursor:
            if row[0] in West:
                row[1] = "W"
                cursor.updateRow(row)
            else:
                row[1] = "E"
                cursor.updateRow(row)

et_dict = {}
with arcpy.da.SearchCursor(et,["ELSUBID","ELCODE","SNAME"]) as cursor:
    for row in cursor:
        et_dict[int(row[0])] = [row[1],row[2]]

with arcpy.da.UpdateCursor(elementRecords,["elem_name","ELCODE"]) as cursor:
    for row in cursor:
        for k,v in et_dict.items():
            if str(k) == str(row[0]):
                row[1]=v[0]
                row[0]=v[1]
                cursor.updateRow(row)

################################################################################
## Create ID review table
################################################################################

id_table = arcpy.TableToTable_conversion(elementRecords,env.workspace,"id_table","dm_stat = 'idrev'")

arcpy.AddField_management(id_table, "Reviewer", "TEXT", "", "", 35)

with arcpy.da.UpdateCursor(id_table, ['ELCODE','Location','Reviewer']) as cursor:
    for row in cursor:
        if row[0] is None:
            pass
        elif row[0].startswith('P') and row[1] == "E":
            row[2] = "rgoad"
        elif row[0].startswith('P') and row[1] == "W":
            row[2] = "sgrund"
        elif row[0].startswith('N'):
            row[2] = "sschuette"
        elif (row[0].startswith('C') or row[0].startswith('H') or row[0].startswith('G')):
            row[2] = "ezimmerman"
        elif row[0].startswith('AB') and row[1] == "E":
            row[2] = "dwatts"
        elif row[0].startswith('AB') and row[1] == "W":
            row[2] = "dyeany"
        elif (row[0].startswith('AR') or row[0].startswith('AA') and row[1] == "E"):
            row[2] = "ceichelberger"
        elif ((row[0].startswith('AR') or row[0].startswith('AA')) and row[1] == "W"):
            row[2] = "rmiller"
        elif row[0].startswith('AM'):
            row[2] = "jwisgo"
        elif row[0].startswith('AF') and row[1] == "E":
            row[2] = "dfischer"
        elif row[0].startswith('AF') and row[1] == "W":
            row[2] = "dfischer"
        elif (row[0].startswith('IMBIV') or row[0].startswith('IMGAS')):
            row[2] = "mwalsh"
        elif (row[0].startswith('IILE') or row[0].startswith('IIODO')) and row[1] == "E":
            row[2] = "bleppo"
        elif (row[0].startswith('IILE') or row[0].startswith('IIODO')) and row[1] == "W":
            row[2] = "pwoods"
        elif row[0].startswith('IILAR'):
            row[2] = "cbier"
        elif row[0].startswith('II') and row[1] == "E":
            row[2] = "bleppo"
        elif row[0].startswith('II') and row[1] == "W":
            row[2] = "pwoods"
        elif row[0].startswith('I') and row[1] == "E":
            row[2] = "bleppo"
        elif row[0].startswith('I') and row[1] == "W":
            row[2] = "pwoods"
        else:
            pass
        cursor.updateRow(row)

with arcpy.da.SearchCursor(id_table, "Reviewer") as cursor:
    reviewers = sorted({row[0] for row in cursor if row[0] is not None})

for reviewer in reviewers:
    if reviewer is None:
        pass
    else:
        id_dict = {}
        with arcpy.da.SearchCursor(id_table,["refcode","element_type","elem_name","ELCODE","elem_found","id_prob_comm","specimen_taken","specimen_count","specimen_desc","curatorial_meth", "specimen_repo","voucher_photo",
        "dm_stat","dm_stat_comm","created_user","created_date","COUNTY_NAM","X","Y"],"Reviewer = '{}'".format(reviewer)) as cursor:
            for row in cursor:
                id_dict[row[0]] = [row[1],row[2],row[3],row[4],row[5],row[6],row[7],row[8],row[9],row[10],row[11],row[12],row[13],row[14],row[15],row[16],row[17],row[18]]

        # write to .csv file
        with open(os.path.join(ReportsPath,'ID Reviewers Status Reports',reviewer+' ID Reviewers Status Report ' + time.strftime("%d%b%Y")+'.csv'), 'wb') as csvfile:
            csv_output = csv.writer(csvfile)
            csv_output.writerow(['Reference Code','Feature Type','Scientific Name','ELCODE','Element found?','Any problems with ID?','Specimen taken?','Specimen Count','Specimen Description','Curatorial Method','Specimen Repository','Voucher Photo',
            'DM Status','DM Status Comments','Created User','Created Date','County','X','Y'])
            for key in sorted(id_dict.keys()):
                csv_output.writerow([key] + id_dict[key])

print("ID Reviewers Status Report Created!")

################################################################################
## Create DM Status Reports
################################################################################

# if record is marked as archived and not listed as dm ready, tag as archived
with arcpy.da.UpdateCursor(elementRecords,["dm_stat","archive"]) as cursor:
    for row in cursor:
        if row[1] == 'Y' and row[0] != "dmready":
            row[0] = "Archived"
            cursor.updateRow(row)

## Create pivot table
stats = arcpy.Statistics_analysis(elementRecords, os.path.join(env.workspace,"stats"), "refcode COUNT;dm_stat COUNT", "refcode;dm_stat")
pivot = arcpy.PivotTable_management(stats,  'refcode', 'dm_stat', 'FREQUENCY', os.path.join(env.workspace, "pivot"))

# add field and populate with 0 if all columns are null
arcpy.AddField_management(pivot, "total_records", "DOUBLE", field_length = 3)
with arcpy.da.UpdateCursor(pivot,["total_records","Archived","dmpend","dmproc","dmready","dr","idprob","idrev"]) as cursor:
    for row in cursor:
        newrow = [0 if x == None else x for x in row]
        cursor.updateRow(newrow)

# populate total records field with sum of records
with arcpy.da.UpdateCursor(pivot,["total_records","Archived","dmpend","dmproc","dmready","dr","idprob","idrev"]) as cursor:
    for row in cursor:
        row[0] = row[1]+row[2]+row[3]+row[4]+row[5]+row[6]+row[7]
        cursor.updateRow(row)

# join survey site fields, county name, and created/last edited fields
arcpy.JoinField_management(pivot, "refcode", "survey_site1", "refcode", ["dm_stat", "dm_stat_comm", "elem_found"])
arcpy.JoinField_management(pivot, "refcode", elementRecords, "refcode", ["COUNTY_NAM", "created_user", "created_date", "last_up_by", "last_up_on"])

# add new field for east or west location
pivot = arcpy.AddField_management(pivot, "Location", "TEXT", "", "", 1, "Location", "", "", "")
# list of western counties
West = ["ERIE", "CRAWFORD", "MERCER", "LAWRENCE", "BEAVER", "WASHINGTON", "GREENE", "VENANGO", "BUTLER", "ALLEGHENY", "FAYETTE", "WESTMORELAND",
"ARMSTRONG", "INDIANA", "CLARION", "JEFFERSON", "FOREST", "WARREN", "MCKEAN", "ELK", "CLEARFIELD", "CAMBRIA", "SOMERSET", "BEDFORD", "BLAIR",
"CENTRE", "CLINTON", "POTTER", "CAMERON", "HUNTINGDON", "FULTON"]
# populate location field with east or west depending if they are in list
with arcpy.da.UpdateCursor(pivot, ["COUNTY_NAM", "Location"]) as cursor:
    for row in cursor:
            if row[0] in West:
                row[1] = "W"
                cursor.updateRow(row)
            else:
                row[1] = "E"
                cursor.updateRow(row)
# if created username has WPC at the end, remove WPC characters
with arcpy.da.UpdateCursor(pivot, "created_user", "refcode IS NOT NULL") as cursor:
    for row in cursor:
        if "WPC" in row[0] or "wpc" in row[0]:
            row[0] = (row[0])[:-3]
            cursor.updateRow(row)

# add field for survey status
pivot = arcpy.AddField_management(pivot,"survey_status","TEXT","","",15)

# calculate survey status
with arcpy.da.UpdateCursor(pivot,["Archived","dmpend","dmproc","dmready","dr","idprob","idrev","total_records","dm_stat","survey_status"]) as cursor:
    for row in cursor:
        if row[1] != 0:
            row[9] = 'Pending'
            cursor.updateRow(row)
        elif (row[0] + row[2] == row[7]) and (row[8] == 'dmproc'):
            row[9] = 'Processed'
            cursor.updateRow(row)
        elif row[0] == row[7]:
            row[9] = 'Archived'
            cursor.updateRow(row)
        elif (row[0] + row[2] + row[3] == row[7]) and (row[0] != row[7]) and ((row[8] == 'dmready') or (row[8] == 'dmproc')):
            row[9] = 'Ready'
            cursor.updateRow(row)
        else:
            row[9] = 'Not Ready'
            cursor.updateRow(row)

# delete surveys that are totally processed
with arcpy.da.UpdateCursor(pivot,"survey_status") as cursor:
    for row in cursor:
        if row[0] == 'Processed':
            cursor.deleteRow()

# create dictionary to hold all attributes
summary_dict = {}
with arcpy.da.SearchCursor(pivot,["refcode","survey_status","Archived","dmpend","dmproc","dmready","dr","idprob","idrev","total_records","dm_stat","dm_stat_comm","elem_found","created_user","created_date","COUNTY_NAM","Location"]) as cursor:
    for row in cursor:
        summary_dict[row[0]] = [row[1],row[2],row[3],row[4],row[5],row[6],row[7],row[8],row[9],row[10],row[11],row[12],row[13],row[14],row[15],row[16]]

# write to .csv file
with open(os.path.join(ReportsPath,'DM Status Reports','DM_Total_'+time.strftime("%d%b%Y")+'.csv'), 'wb') as csvfile:
    csv_output = csv.writer(csvfile)
    # write heading rows to .csv
    csv_output.writerow(['Reference Code','Survey Status','Archived','DM Pending','DM Processed','DM Ready','Draft','ID Problems','ID Review','Total Records','Survey Site DM Status','Survey Site DM Status Comments','Elements Found?','Created User','Created Date','County','Location'])
    # write dictionary rows to .csv
    for key in sorted(summary_dict.keys()):
        csv_output.writerow([key] + summary_dict[key])

# create dictionary of all surveys that are ready for DM
ready_dict = {}
with arcpy.da.SearchCursor(pivot,["refcode","survey_status","Archived","dmpend","dmproc","dmready","dr","idprob","idrev","total_records","dm_stat","dm_stat_comm","elem_found","created_user","created_date","COUNTY_NAM","Location"],"survey_status = 'Ready'") as cursor:
    for row in cursor:
        ready_dict[row[0]] = [row[1],row[2],row[3],row[4],row[5],row[6],row[7],row[8],row[9],row[10],row[11],row[12],row[13],row[14],row[15],row[16]]

# write to .csv file
with open(os.path.join(ReportsPath,'DM Status Reports','DM_Ready_'+time.strftime("%d%b%Y")+'.csv'), 'wb') as csvfile:
    csv_output = csv.writer(csvfile)
    csv_output.writerow(['Reference Code','Survey Status','Archived','DM Pending','DM Processed','DM Ready','Draft','ID Problems','ID Review','Total Records','Survey Site DM Status','Survey Site DM Status Comments','Elements Found?','Created User','Created Date','County','Location'])
    for key in sorted(ready_dict.keys()):
        csv_output.writerow([key] + ready_dict[key])

print("DM Status Reports Created!")

################################################################################
## Create Biologist Reports
################################################################################

user_last = ["albert","braund","eichelberger","furedi","gipe","gleason","goad","grund","hnatkovich","johnson","kunsman","mcpherson","miller","pulver","rohrbaug","ryndock","schuette","stauffer","tracey","walsh","watts","wisgo","woods","yeany","zimmerman"]
refcode_inits = []

# create dictionary for all users and create .csv
for user in user_last:
    user_dict = {}
    refcode_init = user.upper()[0:3]
    refcode_inits.append(refcode_init)
    with arcpy.da.SearchCursor(pivot,["refcode", "survey_status", "Archived", "dmpend", "dmproc", "dmready", "dr", "idprob","idrev", "total_records", "dm_stat", "dm_stat_comm", "elem_found", "created_user","created_date", "COUNTY_NAM", "Location"],"(refcode LIKE '%{}%') OR (created_user LIKE '%{}%')".format(refcode_init,user)) as cursor:
        for row in cursor:
            user_dict[row[0]] = [row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], row[13], row[14], row[15], row[16]]

    # write to .csv file
    with open(os.path.join(ReportsPath, 'Biologist Status Reports', user + "_UnprocessedSurveyStatus_" + time.strftime("%d%b%Y") + '.csv'),'wb') as csvfile:
        csv_output = csv.writer(csvfile)
        csv_output.writerow(['Reference Code', 'Survey Status', 'Archived', 'DM Pending', 'DM Processed', 'DM Ready', 'Draft','ID Problems', 'ID Review', 'Total Records', 'Survey Site DM Status', 'Survey Site DM Status Comments', 'Elements Found?', 'Created User', 'Created Date', 'County', 'Location'])
        for key in sorted(user_dict.keys()):
            csv_output.writerow([key] + user_dict[key])

with arcpy.da.SearchCursor(pivot,["created_user"]) as cursor:
    find_users = sorted({row[0].lower() for row in cursor if row[0] is not None})

with arcpy.da.SearchCursor(pivot,["refcode"]) as cursor:
    find_refs = sorted({row[0][3:6] for row in cursor if row[0] is not None})

other_users = []
for l in find_users:
    if l[2:] in user_last or l[1:] in user_last:
        pass
    else:
        other_users.append(l)

other_refs = []
for l in find_refs:
    if l in refcode_inits:
        pass
    else:
        other_refs.append(l)

other_dict = {}
for code in other_refs:
    with arcpy.da.SearchCursor(pivot,["refcode", "survey_status", "Archived", "dmpend", "dmproc", "dmready", "dr", "idprob","idrev", "total_records", "dm_stat", "dm_stat_comm", "elem_found", "created_user","created_date", "COUNTY_NAM", "Location"],"(refcode LIKE '%{}%')".format(code)) as cursor:
        for row in cursor:
            other_dict[row[0]] = [row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], row[13], row[14], row[15], row[16]]
for code in other_users:
    with arcpy.da.SearchCursor(pivot,["refcode", "survey_status", "Archived", "dmpend", "dmproc", "dmready", "dr", "idprob","idrev", "total_records", "dm_stat", "dm_stat_comm", "elem_found", "created_user","created_date", "COUNTY_NAM", "Location"],"(created_user LIKE '%{}%')".format(code)) as cursor:
        for row in cursor:
            other_dict[row[0]] = [row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], row[13], row[14], row[15], row[16]]

# write to .csv file
with open(os.path.join(ReportsPath, 'Biologist Status Reports', "_User_UnprocessedSurveyStatus_" + time.strftime("%d%b%Y") + '.csv'),'wb') as csvfile:
    csv_output = csv.writer(csvfile)
    csv_output.writerow(['Reference Code', 'Survey Status', 'Archived', 'DM Pending', 'DM Processed', 'DM Ready', 'Draft','ID Problems', 'ID Review', 'Total Records', 'Survey Site DM Status', 'Survey Site DM Status Comments', 'Elements Found?', 'Created User', 'Created Date', 'County', 'Location'])
    for key in sorted(other_dict.keys()):
        csv_output.writerow([key] + other_dict[key])

for ref,name in zip(refcode_inits,user_last):
    incomplete_dict = {}
    with arcpy.da.SearchCursor(elementRecords,["refcode","element_type","elem_name","ELCODE","elem_found","id_prob_comm","specimen_taken","specimen_count","specimen_desc","curatorial_meth", "specimen_repo","voucher_photo",
        "dm_stat","dm_stat_comm","created_user","created_date","COUNTY_NAM","X","Y"],"((refcode LIKE '%{}%') OR (created_user LIKE '%{}%')) AND (dm_stat <> 'dmproc' AND dm_stat <> 'dmready')".format(ref,name)) as cursor:
        for row in cursor:
            incomplete_dict[row[0]] = [row[1],row[2],row[3],row[4],row[5],row[6],row[7],row[8],row[9],row[10],row[11],row[12],row[13],row[14],row[15],row[16],row[17],row[18]]

    # write to .csv file
    with open(os.path.join(ReportsPath, 'Biologist Status Reports', name + "_IncompleteRecords_" + time.strftime("%d%b%Y") + '.csv'),'wb') as csvfile:
        csv_output = csv.writer(csvfile)
        csv_output.writerow(['Reference Code','Feature Type','Scientific Name','ELCODE','Element found?','Any problems with ID?','Specimen taken?','Specimen Count','Specimen Description','Curatorial Method','Specimen Repository','Voucher Photo',
            'DM Status','DM Status Comments','Created User','Created Date','County','X','Y'])
        for key in sorted(incomplete_dict.keys()):
            csv_output.writerow([key] + incomplete_dict[key])

print("DM Biologist Report Created!")
