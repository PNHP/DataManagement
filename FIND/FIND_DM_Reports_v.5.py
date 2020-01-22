#-------------------------------------------------------------------------------
# Name:        FIND Data Management Report Creator
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
print "Welcome to FIND Data Mangement Report Creator. You will be prompted " \
"to choose from the following reports:"
print "DM Total - This report will return a summary of all records currently " \
"in the FIND database"
print "DM Ready - This report will return all records in the FIND database " \
"that are ready to be processed by the data management team"
print "DM Pending - This report will return all records that are listed as " \
"DM Pending"
print "DM Biologist - This report will return a separate report for each " \
"biologist that includes the status of all records belonging to them"
print "DM Reviewer - This report will return a separate report for each " \
"ID reviewer that includes information about records ready for them to review"
print "DM All - This report will return all of the aforementioned reports"

# import system modules
import arcpy, os, datetime
from arcpy import env
from arcpy.sa import *

# Set tools to overwrite existing outputs
arcpy.env.overwriteOutput = True

################################################################################
# Define global variables and functions to be used throughout toolbox
################################################################################

# define env.workspace - this space is used for all temporary files
env.workspace = r'in_memory'

et = r'P:\Conservation Programs\Natural Heritage Program\Data Management\Biotics Database Areas\Element Tracking\current element lists\2018-03-29 complete EST.xlsx'

# file names of the five element feature classes in the FIND enterprise GDB
input_features = ["FIND.DBO.el_pt", "FIND.DBO.el_line", "FIND.DBO.comm_poly",
"FIND.DBO.comm_pt", "FIND.DBO.el_poly", "FIND.DBO.survey_poly"]

# file names that are used for temporary output element feature classes
elementShapefiles = ["element_point", "element_line", "community_poly",
"community_point", "element_poly", "survey_site"]

# file names that are used for temporary element tables
elementTables = ["element_point1", "element_line1","community_poly1",
"community_point1", "element_poly1", "survey_site1"]

# path to FIND enterprise database
elementGDB = r"Database Connections\\FIND.Working.pgh-gis0.sde"

# path to county layer
counties = r'Database Connections\StateLayers.Default.pgh-gis0.sde\StateLayers.DBO.Boundaries_Political\StateLayers.DBO.County'

# path to folder where DM reports will be saved as Excel files
ReportsPath = "P:\Conservation Programs\Natural Heritage Program\Data Management" \
"\Instructions, procedures and documentation\FIND\FIND_2019\Reports"

def countyinfo(elementGDB, counties):
    '''function that loops through each element shapefile and assigns county
    name to features based on spatial location'''

    for ins, output in zip(input_features, elementShapefiles):
        target_features = os.path.join(elementGDB, ins)
        join_features = counties
        element_features = os.path.join(env.workspace, output)

##        # create fieldmap
##        fieldmappings = arcpy.FieldMappings()
##        fieldmappings.addTable(target_features)
##        fieldmappings.addTable(counties)

##        # fields to be kept after spatial join
##        keepFields = ["OID", "OBJECTID", "SHAPE", "SHAPE.STLength()", "SHAPE.STArea()", "COUNTY_NAM", "refcode",
##        "created_user", "created_date", "dm_stat", "dm_stat_comm", "last_up_by",
##        "last_up_on", "element_type", "elem_name", "id_prob",
##        "id_prob_comm", "specimen_taken", "specimen_count", "specimen_desc",
##        "curatorial_meth", "specimen_repo", "voucher_photo", "elem_found", "X", "Y"]

##        # remove all fields not in keep fields from field map
##        for field in fieldmappings.fields:
##            if field.name not in keepFields:
##                fieldmappings.removeFieldMap(fieldmappings.findFieldMapIndex
##                (field.name))

        # run the spatial join tool
        spatial_join = arcpy.SpatialJoin_analysis(target_features, join_features,
        element_features)

        fields = arcpy.ListFields(spatial_join)
        keepFields = ["OID", "OBJECTID", "SHAPE", "SHAPE.STLength()", "SHAPE.STArea()", "COUNTY_NAM", "refcode",
        "created_user", "created_date", "eoid", "BioticsSFID", "dm_stat", "dm_stat_comm", "last_up_by",
        "last_up_on", "element_type", "elem_name", "id_prob",
        "id_prob_comm", "specimen_taken", "specimen_count", "specimen_desc",
        "curatorial_meth", "specimen_repo", "voucher_photo", "elem_found", "X", "Y"]
        dropFields = [x.name for x in fields if x.name not in keepFields]
        arcpy.DeleteField_management(spatial_join, dropFields)

def elementType():
    '''function that assigns element type to all features based on name of
    shapefile within which the feature is contained'''

    for elementShapefile in elementShapefiles:
        input_feature = os.path.join(env.workspace, elementShapefile)

        arcpy.AddField_management(input_feature, "element_type", "TEXT",
        field_length = 15, field_alias = "Element Type")

        arcpy.CalculateField_management(input_feature, "element_type",
        "'" + elementShapefile + "'", "PYTHON_9.3")

def mergetables():
    '''function that converts shapefiles to tables and merges all tables'''

    for input, output in zip(elementShapefiles, elementTables):
        input_feature = os.path.join(env.workspace, input)
        table = arcpy.TableToTable_conversion(input_feature, env.workspace,
        output)

    merge = os.path.join(env.workspace, "elementRecords")
    arcpy.Merge_management(elementTables, merge)

def CreatePivotTable(inTable, outTable):
    '''function that calculates statistics and creates pivot table'''

    arcpy.Statistics_analysis(inTable, outTable, "refcode COUNT;dm_stat COUNT",
    "refcode;dm_stat")

    arcpy.PivotTable_management(outTable, 'refcode', 'dm_stat', 'FREQUENCY',
    os.path.join(env.workspace, "pivotTable"))

def manipulateTable(pivotTable):
    '''function that makes format changes to pivot table'''

    # delete records with null or blank reference code
    with arcpy.da.UpdateCursor(pivotTable, 'refcode') as cursor:
        for row in cursor:
            if row[0] == None or row[0] == "":
                cursor.deleteRow()

    # add field and populate with total number of records by adding all records
    arcpy.AddField_management(pivotTable, "total_records", "DOUBLE",
    field_length = 3, field_alias = "Total Records")
    expression = "!dmpend! + !dmproc! + !dmready! + !dr! + !idrev!"
    arcpy.CalculateField_management(pivotTable, "total_records", expression,
    "PYTHON_9.3")

    # join dm status and dm status comments data from survey site to pivot table
    join = os.path.join(env.workspace, "survey_site1")
    arcpy.AlterField_management(join, "dm_stat", "survey_site_dmstat",
    "Survey Site - DM Status")
    arcpy.JoinField_management(pivotTable, "refcode", join, "refcode",
    ["survey_site_dmstat", "dm_stat_comm", "elem_found"])

    # join original data from elementRecords table to pivot table
    join = os.path.join(env.workspace, "elementRecords")
    arcpy.JoinField_management(pivotTable, "refcode", join, "refcode",
    ["COUNTY_NAM", "created_user", "created_date", "last_up_by", "last_up_on",
    "element_type"])

    # add new field for east or west location
    arcpy.AddField_management(pivotTable, "Location", "TEXT", "", "", 1,
    "Location", "", "", "")
    # list of western counties
    West = ["ERIE", "CRAWFORD", "MERCER", "LAWRENCE", "BEAVER", "WASHINGTON",
    "GREENE", "VENANGO", "BUTLER", "ALLEGHENY", "FAYETTE", "WESTMORELAND",
    "ARMSTRONG", "INDIANA", "CLARION", "JEFFERSON", "FOREST", "WARREN",
    "MCKEAN", "ELK", "CLEARFIELD", "CAMBRIA", "SOMERSET", "BEDFORD", "BLAIR",
    "CENTRE", "CLINTON", "POTTER", "CAMERON", "HUNTINGDON", "FULTON"]
    # populate location field with east or west depending if they are in list
    with arcpy.da.UpdateCursor(pivotTable, ["COUNTY_NAM", "Location"]) as cursor:
        for row in cursor:
                if row[0] in West:
                    row[1] = "W"
                    cursor.updateRow(row)
                else:
                    row[1] = "E"
                    cursor.updateRow(row)
    with arcpy.da.UpdateCursor(pivotTable, "created_user") as cursor:
        for row in cursor:
            if "WPC" in row[0]:
                row[0] = (row[0])[:-3]
                cursor.updateRow(row)

def dmtotal(pivotTable):
    '''function that creates report of all unprocessed records in FIND'''

    # create copy of pivot table
    pivotTableCOPY = arcpy.TableToTable_conversion(pivotTable, env.workspace,
    "pivotTableCOPY")

    # delete records when all features are processed
    with arcpy.da.UpdateCursor(pivotTableCOPY, ["dmproc", "total_records",
    "survey_site_dmstat"]) as cursor:
        for row in cursor:
            if row[0] == row[1] and row[2] == "dmproc":
                cursor.deleteRow()
            elif row[0] == row[1] and row[2] is None:
                cursor.deleteRow()
            else:
                pass
    # export table as Excel file to produce final report
    filename = "DM Total " + time.strftime("%d%b%y")+".xls"
    outTable = os.path.join(ReportsPath, "DM Status Reports", filename)
    arcpy.TableToExcel_conversion(pivotTableCOPY, outTable)

def dmready(pivotTable):
    '''function that creates report of all records that are ready for DM'''

    # create copy of pivot table
    pivotTableCOPY = arcpy.TableToTable_conversion(pivotTable, env.workspace,
    "pivotTableCOPY")

    # delete all records unless all features and survey site are marked dm ready
    with arcpy.da.UpdateCursor(pivotTableCOPY, ["dmready","dmproc", "total_records",
    "survey_site_dmstat"]) as cursor:
        for row in cursor:
            if (row[0]+row[1] == row[2]) and (row[0] > 0) and (row[3] == "dmready" or row[3] == "dmproc"):
                pass
            else:
                cursor.deleteRow()

    # export table as Excel file to produce final report
    filename = "DM Ready " + time.strftime("%d%b%y")+".xls"
    outTable = os.path.join(ReportsPath, "DM Status Reports", filename)
    arcpy.TableToExcel_conversion(pivotTableCOPY, outTable)
    print "DM Ready Report Created!"

def dmpending(pivotTable):
    '''function that creates report of records with at least one feature marked
    as DM Pending'''

    # create copy of pivot table
    pivotTableCOPY = arcpy.TableToTable_conversion(pivotTable, env.workspace,
    "pivotTableCOPY")

    # delete all records that do not have at least one feature marked DM Pending
    with arcpy.da.UpdateCursor(pivotTableCOPY, "survey_site_dmstat") as cursor:
        for row in cursor:
            if row[0] == "dmpend":
                pass
            else:
                cursor.deleteRow()

    # export table as Excel file to produce final report
    filename = "DM Pending " + time.strftime("%d%b%y")+".xls"
    outTable = os.path.join(ReportsPath, "DM Status Reports", filename)
    arcpy.TableToExcel_conversion(pivotTableCOPY, outTable)
    print "DM Pending Report Created!"

def dmbiologist(pivotTable):
    pivotTableCOPY = arcpy.TableToTable_conversion(pivotTable, env.workspace,
    "pivotTableCOPY")
    with arcpy.da.UpdateCursor(pivotTableCOPY, ["dmproc", "total_records",
    "survey_site_dmstat"]) as cursor:
        for row in cursor:
            if row[0] == row[1] and (row[2] == "dmproc" or row[2] is None):
                cursor.deleteRow()
            else:
                pass

    refname = ["hna", "geo", "lep", "eic", "tra", "dwa", "yea", "zim", "eaz",
    "alb", "kun", "mcp", "mil", "wis", "gip", "fur", "wal", "wat", "woo", "gle",
    "gru", "sch", "shc", "dav", "roh", "bra", "goa", "sit"]
    createnames = ["ahnatkovich", "bgeorgic", "bleppo", "ceichelberger",
    "ctracey", "dwatts", "dyeany", "ezimmerman", "ezimmerman", "jalbert",
    "jkunsman", "jmcpherson", "rmiller", "jwisgo", "kgipe", "mfuredi", "mwalsh",
    "dwatts", "pwoods", "rgleason", "sgrund", "sschuette", "sschuette",
    "ezimmerman", "anrohrbaug", "jbraund", "rgoad", "kesitch"]
    for ref, name in zip(refname, createnames):
        with arcpy.da.UpdateCursor(pivotTableCOPY, ["refcode", "created_user"]) as cursor:
            for row in cursor:
                if row[0] is None or row[1] is None:
                    pass
                else:
                    if (row[1].lower() == "arcgis" or row[1].lower() ==
                    "tjadmin" or row[1].lower() == "administrator" or
                    row[1].lower() == "bgeorgic") and ref in row[0].lower():
                        row[1] = name
                        cursor.updateRow(row)

    outPath = "P:\\Conservation Programs\\Natural Heritage Program\\" \
    "Data Management\\Instructions, procedures and documentation\\FIND\\" \
    "FIND_2019\\Reports\\Biologist Status Reports"

    with arcpy.da.SearchCursor(pivotTableCOPY, "created_user") as cursor:
        biologists = sorted({row[0] for row in cursor})

    for biologist in biologists:
        if biologist is None:
            pass
        else:
            expression = "created_user = '{}'".format(biologist)
            tableTEMP = arcpy.TableToTable_conversion(pivotTableCOPY,
            "in_memory", "tableTEMP", expression)
            filename = biologist + " - " + "FIND Status Report " + time.strftime("%d%b%Y")+".xls"
            outTable = os.path.join(outPath, filename)
            arcpy.TableToExcel_conversion(tableTEMP, outTable)
    print "DM Biologist Report Created!"

def idreview(elementRecords):
    with arcpy.da.UpdateCursor(elementRecords, ["dm_stat"]) as cursor:
        for row in cursor:
            if row[0] != "idrev":
                cursor.deleteRow()

    ETtableEXCEL = r'P:\\Conservation Programs\\Natural Heritage Program' \
    '\\Data Management\\Instructions, procedures and documentation\\FIND\\FIND_2017' \
    '\\DM Documentation\\Admin and Maintenance\\20170321_ET.csv'
    arcpy.TableToTable_conversion (ETtableEXCEL, "in_memory", "ETtable")
    arcpy.JoinField_management(elementRecords, "elem_name",
    "in_memory\\ETtable", "ELEMENT_SUBNATIONAL_ID", ["ELEMENT_CODE",
    "SCIENTIFIC_NAME"])

    arcpy.AddField_management(elementRecords, "Location", "TEXT", "", "", 1,
    "Location", "", "", "")

    West = ["ERIE", "CRAWFORD", "MERCER", "LAWRENCE", "BEAVER", "WASHINGTON",
    "GREENE", "VENANGO", "BUTLER", "ALLEGHENY", "FAYETTE", "WESTMORELAND",
    "ARMSTORNG", "INDIANA", "CLARION", "JEFFERSON", "FOREST", "WARREN",
    "MCKEAN", "ELK", "CLEARFIELD", "CAMBRIA", "SOMERSET", "BEDFORD", "BLAIR",
    "CENTRE", "CLINTON", "POTTER", "CAMERON", "HUNTINGDON", "FULTON",
    "FRANKLIN"]
    with arcpy.da.UpdateCursor(elementRecords, ["COUNTY_NAM", "Location"]) as cursor:
        for row in cursor:
                if row[0] in West:
                    row[1] = "W"
                    cursor.updateRow(row)
                else:
                    row[1] = "E"
                    cursor.updateRow(row)

    with arcpy.da.UpdateCursor(elementRecords, "ELEMENT_CODE") as cursor:
        for row in cursor:
            if row[0] is None:
                cursor.deleteRow()

    arcpy.AddField_management(elementRecords, "Reviewer", "TEXT", "", "", 35,
    "ID Reviewer", "", "", "")

    with arcpy.da.UpdateCursor(elementRecords, ['ELEMENT_CODE', 'Location',
    'Reviewer']) as cursor:
        for row in cursor:
            if row[0].startswith('P') and row[1] == "E":
                row[2] = "jkunsman"
            elif row[0].startswith('P') and row[1] == "W":
                row[2] = "sgrund"
            elif row[0].startswith('N'):
                row[2] = "sschuette"
            elif (row[0].startswith('C') or row[0].startswith('H') or
            row[0].startswith('G')):
                row[2] = "ezimmerman"
            elif row[0].startswith('AB') and row[1] == "E":
                row[2] = "dwatts"
            elif row[0].startswith('AB') and row[1] == "W":
                row[2] = "dyeany"
            elif (row[0].startswith('AM') or (row[0].startswith('AR') or
            row[0].startswith('AA')) and row[1] == "E"):
                row[2] = "ceichelberger"
            elif ((row[0].startswith('AR') or row[0].startswith('AA')) and
            row[1] == "W"):
                row[2] = "rmiller"
            elif row[0].startswith('AF') and row[1] == "E":
                row[2] = "Need Reviewer"
            elif row[0].startswith('AF') and row[1] == "W":
                row[2] = "Need Reviewer"
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

    fields = arcpy.ListFields(elementRecords)
    keepFields = ["OID", "COUNTY_NAM", "refcode", "created_user", "created_date",
    "dm_stat", "Reviewer", "dm_stat_comm", "last_up_by", "last_up_on",
    "element_type", "id_prob", "id_prob_comm", "specimen_taken",
    "specimen_count", "specimen_desc", "curatorial_meth", "specimen_repo",
    "voucher_photo", "SCIENTIFIC_NAME", "ELEMENT_CODE", "X", "Y"]
    dropFields = [x.name for x in fields if x.name not in keepFields]
    arcpy.DeleteField_management(elementRecords, dropFields)

    outPath = "P:\\Conservation Programs\\Natural Heritage Program\\" \
    "Data Management\\Instructions, procedures and documentation\\FIND\\" \
    "FIND_2019\\Reports\\ID Reviewers Status Reports"

    with arcpy.da.SearchCursor(elementRecords, "Reviewer") as cursor:
        reviewers = sorted({row[0] for row in cursor})

    for reviewer in reviewers:
        if reviewer is None:
            pass
        else:
            expression = "Reviewer = '{}'".format(reviewer)
            tableTEMP = arcpy.TableToTable_conversion(elementRecords, "in_memory", "tableTEMP", expression)
            filename = reviewer + " - " + "ID Reviewers Status Report " + time.strftime("%d%b%Y")+".xls"
            outTable = os.path.join(outPath, filename)
            arcpy.TableToExcel_conversion(tableTEMP, outTable)
    print "ID Reviewers Status Report Created!"

def dmunprocessed(elementRecords):
    with arcpy.da.UpdateCursor(elementRecords, "element_type") as cursor:
        for row in cursor:
            if row[0] == "survey_site":
                cursor.deleteRow()
    with arcpy.da.UpdateCursor(elementRecords,["eoid","BioticsSFID","dm_stat"]) as cursor:
        for row in cursor:
            if row[0] is None and row[1] is None and row[3] == 'dmproc':
                pass
            else:
                cursor.deleteRow()


################################################################################
# Start Script...
################################################################################

reportType = raw_input("Which report would you like to run? (please enter " \
"'DM Pending', 'DM Ready', 'DM Biologist', 'DM Reviewer', 'DM Total, or DM All')")

countyinfo(elementGDB, counties)

elementType()

mergetables()

if reportType.lower() == "dm reviewer":
    idreview(os.path.join(env.workspace, "elementRecords"))
else:
    CreatePivotTable(os.path.join(env.workspace, "elementRecords"),
    os.path.join(env.workspace, "summaryStats"))

    manipulateTable(os.path.join(env.workspace, "pivotTable"))

    if reportType.lower() == "dm pending":
        dmpending(os.path.join(env.workspace, "pivotTable"))

    elif reportType.lower() == "dm ready":
        dmready(os.path.join(env.workspace, "pivotTable"))

    elif reportType.lower() == "dm biologist":
        dmbiologist(os.path.join(env.workspace, "pivotTable"))

    elif reportType.lower() == "dm total":
        dmtotal(os.path.join(env.workspace, "pivotTable"))

    elif reportType.lower() == "dm all":
        idreview(os.path.join(env.workspace, "elementRecords"))
        dmpending(os.path.join(env.workspace, "pivotTable"))
        dmready(os.path.join(env.workspace, "pivotTable"))
        dmbiologist(os.path.join(env.workspace, "pivotTable"))
        dmtotal(os.path.join(env.workspace, "pivotTable"))
