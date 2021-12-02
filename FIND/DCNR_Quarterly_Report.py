#-------------------------------------------------------------------------------
# Name:        ER Quarterly Report
# Purpose:     Pulls current data from FIND enterprise geodatabase and
#              returns Excel spreadsheet containing a summary of data from the
#              requested report.
# Author:      Molly Moore
# Created:     2016-09-06
# Updated:     2016-09-06 - updated to include options for DM Pending and DM
#              Total reports
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

# Set tools to overwrite existing outputs
arcpy.env.overwriteOutput = True

quarter = raw_input("Enter the quarter for the report (type q1, q2, q3, q4): ")
year = raw_input("Enter the year for the report (YYYY): ")

if quarter.lower() == 'q1':
    q = 04
elif quarter.lower() == 'q2':
    q = 07
elif quarter.lower() == 'q3':
    q = 10
elif quarter.lower() == 'q4':
    q = 01
    year = int(year) + 1
else:
    print "You have not entered a valid response."

# define env.workspace - this space is used for all temporary files
env.workspace = r'in_memory'

# file names of the five element feature classes in the FIND enterprise GDB
input_features = ["FIND2021.DBO.el_pt", "FIND2021.DBO.el_line","FIND2021.DBO.el_poly", "FIND2021.DBO.comm_poly",
"FIND2021.DBO.comm_pt",  "FIND2021.DBO.survey_poly"]

# file names that are used for temporary element tables
elementTables = ["element_point", "element_line", "element_poly", "community_poly",
"community_point", "survey_poly"]

# path to FIND enterprise database
elementGDB = r"Database Connections\\FIND2021.Working.pgh-gis0.sde"

reportPath = r'P:\Conservation Programs\Natural Heritage Program\Data Management\Instructions, procedures and documentation\FIND\FIND_2021\Reports\DCNR Quarterly FIND Reports'

def elementType():
    '''function that assigns element type to all features based on name of
    shapefile within which the feature is contained'''

    for ins, output in zip(input_features, elementTables):
        feature = os.path.join(elementGDB, ins)
        print(feature)

        fieldmappings = arcpy.FieldMappings()
        fieldmappings.addTable(feature)

        # fields to be kept after spatial join
        keepFields = ["OID", "dm_stat", "elem_type", "created_date"]

        # remove all fields not in keep fields from field map
        for field in fieldmappings.fields:
            if field.name not in keepFields:
                fieldmappings.removeFieldMap(fieldmappings.findFieldMapIndex
                (field.name))

        arcpy.TableToTable_conversion(os.path.join(elementGDB, ins), env.workspace, output, "", fieldmappings)

    for table in elementTables:

        arcpy.AddField_management(table, "Feature_Class", "TEXT", field_length = 50, field_alias = "Taxa")

        arcpy.CalculateField_management(table, "Feature_Class", "'" + table + "'", "PYTHON_9.3")

    for table in elementTables[0:3]:
        with arcpy.da.UpdateCursor(table, ['elem_type', 'Feature_Class']) as cursor:
            for row in cursor:
                if row[0] == 0 or row[0] == 1:
                    row[1] = 'Lepidoptera and Other Insects'
                    cursor.updateRow(row)
                elif row [0] == 2:
                    row[1] = 'Other Invertebrates'
                    cursor.updateRow(row)
                elif row[0] == 3:
                    row[1] = 'Plants'
                    cursor.updateRow(row)
                elif row[0] == 4:
                    row[1] = 'Vertebrate Animals'
                    cursor.updateRow(row)

        arcpy.DeleteField_management(table, "elem_type")

    elementRecords = arcpy.CreateTable_management(env.workspace, "elementRecords", "element_point")
    arcpy.Append_management(elementTables, elementRecords)

    with arcpy.da.UpdateCursor(elementRecords, ["dm_stat", "Feature_Class"]) as cursor:
        for row in cursor:
            if row[0] == "dr":
                row[0] = "Draft"
                cursor.updateRow(row)
            if row[0] == "idrev":
                row[0] = "Ready for ID Review"
                cursor.updateRow(row)
            if row[0] == "dmproc":
                row[0] = "DM Processed"
                cursor.updateRow(row)
            if row[0] == "dmready":
                row[0] = "Ready for DM"
                cursor.updateRow(row)
            if row[0] == "dmpend":
                row[0] = "DM Pending"
                cursor.updateRow(row)
##            if row[0] == "idprob":
##                row[0] = "ID Problems"
            if row[1] == "community_poly" or row[1] == "community_point":
                row[1] = "Communities"
                cursor.updateRow(row)
            if row [1] == "survey_poly":
                row[1] = "Survey Sites"
                cursor.updateRow(row)

    with arcpy.da.UpdateCursor(elementRecords, "created_date") as cursor:
        for row in cursor:
            if row[0] > datetime.datetime(int(year), int(q), 01, 0, 0, 0, 0):
                cursor.deleteRow()

    summaryTable = arcpy.Statistics_analysis(elementRecords, "summaryTable", "Feature_Class COUNT;dm_stat COUNT",
    "Feature_Class;dm_stat")

    pivotTable = arcpy.PivotTable_management(summaryTable, 'Feature_Class', 'dm_stat', 'FREQUENCY', "pivotTable")

    arcpy.AddField_management(pivotTable, "Total", "LONG", "", "", 8, "Total")
    with arcpy.da.UpdateCursor(pivotTable,["Total","DM_Pending","DM_Processed","Ready_for_DM","Draft","Ready_for_ID_Review","idprob"]) as cursor:
        for row in cursor:
            row[0] = row[1]+row[2]+row[3]+row[4]+row[5]+row[6]
            cursor.updateRow(row)

    # export table as Excel file to produce final report
    filename = "FIND Quarterly Report " + time.strftime("%d%b%y")+".xls"
    outTable = os.path.join(reportPath, filename)
    arcpy.TableToExcel_conversion(pivotTable, outTable)
    print "DCNR FIND Quarterly Report Created!"

elementType()
