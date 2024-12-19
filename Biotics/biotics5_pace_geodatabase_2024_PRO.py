"""
Name:        Biotics5 Monthly Data Packaging - HGIS File Geodatabase
Purpose:     Creates a version of the Biotics exports to be used for HGIS.
Created:     2014-05-13, updated 2024-11-26 to work with Python 3 and Pro licensing

NOTE: The Biotics shapefiles must be unzipped before running this script
Updates:
2014-05-28: Records in eo value table that do not exist in eo shape were causing TypeError: sequence size must match size of the row. Used if else statement by insert cursor to make the script skip thoise records.
2014-05-21: Updated coordinate system from albers to bof83
2014-05-19: Removed date from output file names
2014-05-19: Changed geodatabase name to Hgis_eo_files.gdb
2014-05-19: Removed aliases
2017-07-12: Changed geodatabase name to pace and added VISITS to SF
2024-11-26: MMOORE - updated to work with Python 3 and Pro and changed spatial referencing objects to use strings instead of Favorites
"""

# Import modules
import arcpy
import os
import shutil
import time
import datetime
import traceback
import sys

# Set tools to overwrite existing outputs
arcpy.env.overwriteOutput = True

# define projections
# using bof prj as environment setting was causing projection issues, geodatabase will be reprojected at end of script - (this should probably be tested again to see if there is more efficient way to handle this - MMOORE)
# define custom albers projection and assign it to output coordinate system environment variable
albers_str = r'PROJCS["alber",GEOGCS["GCS_North_American_1983",DATUM["D_North_American_1983",SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Albers"],PARAMETER["false_easting",0.0],PARAMETER["false_northing",0.0],PARAMETER["central_meridian",-78.0],PARAMETER["standard_parallel_1",40.0],PARAMETER["standard_parallel_2",42.0],PARAMETER["latitude_of_origin",39.0],UNIT["Meter",1.0]];-16085300 -8515400 10000;0 1;0 1;0.001;0.001;0.001;IsHighPrecision'
albers_prj = arcpy.SpatialReference()
albers_prj.loadFromString(albers_str)
arcpy.env.outputCoordinateSystem = albers_prj

# define BOF Lambert coordinate system that will be used for final feature classes
bof_str = r'PROJCS["BOF_Lambert_NAD83",GEOGCS["GCS_North_American_1983",DATUM["D_North_American_1983",SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Lambert_Conformal_Conic"],PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",-78.0],PARAMETER["Standard_Parallel_1",40.25],PARAMETER["Standard_Parallel_2",41.5],PARAMETER["Scale_Factor",1.0],PARAMETER["Latitude_Of_Origin",39.0],UNIT["Foot",0.3048]];-121008700 -96114200 3048;-100000 10000;-100000 10000;3.28083989501312E-03;0.001;0.001;IsHighPrecision'
bof_prj = arcpy.SpatialReference()
bof_prj.loadFromString(bof_str)
bof_spatial_ref = bof_prj

########################################################################################################################
# SET THESE PATH NAMES TO THE CORRECT PATH NAMES ON YOUR LOCAL COMPUTER
########################################################################################################################
# Folder that contains this month's exported shapefiles and the export views. It CANNOT contain the previous months exports.
# THE SHAPEFILES MUST BE UNZIPPED PRIOR TO RUNNING
in_path = r"H:\temp\Biotics_export_testing\pace_test\20241115"
# Folder where the final hgis shapefiles and geodatabase will be located.
out_path = r"H:\temp\Biotics_export_testing\pace_test\20241115\pace"
# Name of the final geodatabase
gdb_name = "PACE_eo_files.gdb"
########################################################################################################################
# END PATH NAME CHANGES
########################################################################################################################

# Using bof prj as environment setting was causing projection issues, geodatabase will be reprojected at end of script
gdb_name_albers = "pace_eo_files_albers.gdb"

# Variable for final geodatabase
pace_gdb = os.path.join(out_path, gdb_name_albers)

# EOR fields for insert cursor
eor_fields = ["FEATURE_ID", "EO_ID", "SHAPE_ID", "EORANK", "SP_CODE", "EODATA", "EST_RA", "DIRECTIONS", "GENDESC",
              "LASTOBS", "SURVEY_DAT", "FIRSTOBS", "BCD_PRECIS", "MGMT_COM", "EORANKCOM", "SNAME", "GRANK", "USESA",
              "SCOMNAME", "SRANK", "SEOTRACK", "SPROT", "CITATION", "SOURCECODE", "ELCODE", "PBS_STATUS", "ID",
              "AGENCYID1", "AGENCYID2", "SHAPE@XY"]

# SF fields for insert cursor
sf_fields = ["FEATURE_ID", "ELCODE", "SNAME", "SCOMNAME", "SF_ID", "EO_ID", "SP_CODE", "SF_DESCRIP", "SF_LOCATOR",
             "USESA", "GRANK", "SRANK", "SPROT", "SEOTRACK", "PBS_STATUS", "VISITS", "SHAPE_ID", "ID", "SHAPE@"]


# Define functions
def add_eor_fields(in_fc):
    """Adds all Element Occurrence Records (EOR) fields to the input feature class, in_fc. This function is
    used to add fields to eo ptreps and eo reps."""
    arcpy.AddField_management(in_fc, "FEATURE_ID", "DOUBLE")
    arcpy.AddField_management(in_fc, "EO_ID", "DOUBLE")
    arcpy.AddField_management(in_fc, "SHAPE_ID", "DOUBLE")
    arcpy.AddField_management(in_fc, "EORANK", "TEXT", field_length=5)
    arcpy.AddField_management(in_fc, "SP_CODE", "DOUBLE")
    arcpy.AddField_management(in_fc, "EODATA", "TEXT", field_length=2147483647)
    arcpy.AddField_management(in_fc, "EST_RA", "TEXT", field_length=20)
    arcpy.AddField_management(in_fc, "DIRECTIONS", "TEXT", field_length=2147483647)
    arcpy.AddField_management(in_fc, "GENDESC", "TEXT", field_length=2147483647)
    arcpy.AddField_management(in_fc, "LASTOBS", "TEXT", field_length=25)
    arcpy.AddField_management(in_fc, "SURVEY_DAT", "TEXT", field_length=25)
    arcpy.AddField_management(in_fc, "FIRSTOBS", "TEXT", field_length=25)
    arcpy.AddField_management(in_fc, "BCD_PRECIS", "TEXT", field_length=5)
    arcpy.AddField_management(in_fc, "MGMT_COM", "TEXT", field_length=2147483647)
    arcpy.AddField_management(in_fc, "EORANKCOM", "TEXT", field_length=2147483647)
    arcpy.AddField_management(in_fc, "SNAME", "TEXT", field_length=200)
    arcpy.AddField_management(in_fc, "GRANK", "TEXT", field_length=20)
    arcpy.AddField_management(in_fc, "USESA", "TEXT", field_length=20)
    arcpy.AddField_management(in_fc, "SCOMNAME", "TEXT", field_length=400)
    arcpy.AddField_management(in_fc, "SRANK", "TEXT", field_length=20)
    arcpy.AddField_management(in_fc, "SEOTRACK", "TEXT", field_length=1)
    arcpy.AddField_management(in_fc, "SPROT", "TEXT", field_length=20)
    arcpy.AddField_management(in_fc, "CITATION", "TEXT", field_length=2147483647)
    arcpy.AddField_management(in_fc, "SOURCECODE", "TEXT", field_length=2147483647)
    arcpy.AddField_management(in_fc, "ELCODE", "TEXT", field_length=10)
    arcpy.AddField_management(in_fc, "PBS_STATUS", "TEXT", field_length=20)
    arcpy.AddField_management(in_fc, "ID", "DOUBLE")
    arcpy.AddField_management(in_fc, "AGENCYID1", "SHORT")
    arcpy.AddField_management(in_fc, "AGENCYID2", "SHORT")


def add_sf_fields(in_fc):
    """Adds all Source Feature (SF) fields to the input feature class, in_fc. This function is
    used to add fields to source lines, points, and polygons."""
    arcpy.AddField_management(in_fc, "FEATURE_ID", "DOUBLE")
    arcpy.AddField_management(in_fc, "ELCODE", "TEXT", field_length=10)
    arcpy.AddField_management(in_fc, "SNAME", "TEXT", field_length=200, field_alias="Scientific Name")
    arcpy.AddField_management(in_fc, "SCOMNAME", "TEXT", field_length=400, field_alias="Common Name")
    arcpy.AddField_management(in_fc, "SF_ID", "DOUBLE")
    arcpy.AddField_management(in_fc, "EO_ID", "DOUBLE")
    arcpy.AddField_management(in_fc, "SP_CODE", "DOUBLE", field_alias="Species Code")
    arcpy.AddField_management(in_fc, "SF_DESCRIP", "TEXT", field_length=250, field_alias="SF Descriptor")
    arcpy.AddField_management(in_fc, "SF_LOCATOR", "TEXT", field_length=250, field_alias="SF Locator")
    arcpy.AddField_management(in_fc, "USESA", "TEXT", field_length=20, field_alias="ESA Status")
    arcpy.AddField_management(in_fc, "GRANK", "TEXT", field_length=20, field_alias="Global Rank")
    arcpy.AddField_management(in_fc, "SRANK", "TEXT", field_length=20, field_alias="State Rank")
    arcpy.AddField_management(in_fc, "SPROT", "TEXT", field_length=50, field_alias="State Protection")
    arcpy.AddField_management(in_fc, "SEOTRACK", "TEXT", field_length=1, field_alias="Tracked")
    arcpy.AddField_management(in_fc, "PBS_STATUS", "TEXT", field_length=10, field_alias="PBS Status")
    arcpy.AddField_management(in_fc, "VISITS", "TEXT", field_length=2147483647, field_alias="Visits")
    arcpy.AddField_management(in_fc, "SHAPE_ID", "DOUBLE")
    arcpy.AddField_management(in_fc, "ID", "DOUBLE")


def excel_to_value_table(biotics_or_pace, work_gdb, eo_or_sf):
    """Loops through Excel tables, using hgis or biotics wildcard, in the in_path.
    Converts Excel tables to GIS tables. Builds value table based on attributes
    in GIS tables. Returns eo or sf value table."""
    wildcard = "{0}_{1}*.xlsx".format(biotics_or_pace, eo_or_sf)
    # Use enumerate function so n will be count of loops starting at 1
    # n will be used to name the tables
    for n, f in enumerate(arcpy.ListFiles(wildcard), 1):
        # Variable for the input table
        in_table = os.path.join(in_path, f)
        # The output table is named based on eor or sf and the loop count, n
        out_name = "{0}_table_{1}".format(eo_or_sf, n)
        out_table = os.path.join(work_gdb, out_name)
        # Convert excel table to GIS
        arcpy.ExcelToTable_conversion(in_table, out_table)
        """Note about why ExcelToTable tool was used:
        Accessing csv directly via csv module -> Unicode errors
        MakeTableView -> Long text fields came out null or were skipped
        TableToTable tool -> Truncated long text fields to 254 even with geodatabase table as output"""
    # ---- Loop through newly created GIS tables and create value table
    # Set the workspace so ListTables will list the tables in the geodatabase
    arcpy.env.workspace = work_gdb
    # Use wildcard to list either eo or sf tables
    wildcard = "{}_table*".format(eo_or_sf)
    # value_table will be a list of lists, which is like a table
    value_table = []
    # Loop through tables
    tables = arcpy.ListTables(wildcard)
    for table in tables:
        # Use search cursor to retrieve all attributes from table
        srows = arcpy.da.SearchCursor(table, "*")
        for srow in srows:
            # The search cursor row data type is a tuple, so we convert it to a list
            row = list(srow)
            # Append the list of values to the value table
            # Python slice notation is used to exclude the first column since it is OBJECTID
            value_table.append(row[1:])
        # Delete tables after use
        arcpy.Delete_management(table)
    """Note why we loop through GIS tables instead of merging into 1 GIS table:
    When converting Excel to GIS, the GIS text field will be the minimum it needs
    to be for that Excel table. If a preceding GIS table in the Merge has a shorter
    max text length then the next, the tool will fail."""
    # Set the workspace back to in_path
    arcpy.env.workspace = in_path
    return value_table


########################################################################################################################
print("Starting script at {}".format(datetime.datetime.now().strftime("%H:%M:%S")))
########################################################################################################################

# Set environment workspace
arcpy.env.workspace = in_path

########################################################################################################################
print("Creating PACE Biotics geodatabase at {}".format(datetime.datetime.now().strftime("%H:%M:%S")))
########################################################################################################################

# If it already exists, delete it
if os.path.exists(pace_gdb):
    shutil.rmtree(pace_gdb)
# Create HGIS Biotics geodatabase
arcpy.CreateFileGDB_management(out_path, gdb_name_albers)

########################################################################################################################
print("Creating value tables from table views at {}".format(datetime.datetime.now().strftime("%H:%M:%S")))
########################################################################################################################

# Create value tables using excel_to_value_table function defined at top of script
eor_values = excel_to_value_table("pace", pace_gdb, "eo")
sf_values = excel_to_value_table("pace", pace_gdb, "sf")

# For EOR values, calculate ID, AGENCYID1, and AGENCYID2 fields and add to value table
count = 0
for row in eor_values:
    count += 1
    row.append(count)
    row.append(0)
    row.append(0)

# For SF values, calculate ID field and add to value table
count = 0
for row in sf_values:
    count += 1
    row.append(count)

########################################################################################################################
print("Creating eo ptreps at {}".format(datetime.datetime.now().strftime("%H:%M:%S")))
########################################################################################################################

# ---- Calculate geometry for eo ptreps and append to value table (get geometery from eo shape XY fields)
# Create variable for eo shape, using star wildcard to grab the file that starts with EO_SHAPE
for f in arcpy.ListFeatureClasses("EO_SHAPE*"):
    eo_shape = f
# Use search cursor to get XY coordinates from eo shapefile
srows = arcpy.da.SearchCursor(eo_shape, ["X", "Y", "EO_ID"])
for srow in srows:
    # Combine the X and Y values as a tuple
    shape_xy = (srow[0], srow[1])
    # Get EO ID of search cursor row
    eoid = srow[2]
    for row in eor_values:
        # Look up the corresponding record in the value table
        if row[1] == eoid:
            # Append the tuple to the end of the row, so it can later be inserted as the SHAPE@XY geometry token
            row.append(shape_xy)
            break

# ---- Create eoptreps
# Create eo ptreps
arcpy.CreateFeatureclass_management(pace_gdb, "eo_pt_lyr", "POINT")
# Create variable to hold full pathname of eo ptreps
eo_ptreps = os.path.join(pace_gdb, "eo_pt_lyr")
# Add eor fields using function defined at top of script
add_eor_fields(eo_ptreps)
# Insert eor values using insert cursor
cursor = arcpy.da.InsertCursor(eo_ptreps, eor_fields)
for row in eor_values:
    try:
        # Catch records that have no geometry attribute
        # because there are records in the value table that are not in the shapefile
        if len(eor_fields) == 30 and len(row) == 29:
            # Skip those records
            pass
        else:
            cursor.insertRow(row)
    except:
        print("{0}: {1} Failed at {2}".format("EO ID", row[1], datetime.datetime.now().strftime("%H:%M:%S")))
        # Get traceback object
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        # Concate information together concerning th error into a message string
        pymsg = "PYTHON ERRORS:\nTraceback info:\n" + tbinfo + "\nError Info:\n" + str(sys.exc_info()[1])
        msgs = "ArcPy ERRORS:\n" + arcpy.GetMessages(2) + "\n"
        # Return python error messages
        print(pymsg)
        print(msgs)
del cursor

########################################################################################################################
print("Creating eo reps at {}".format(datetime.datetime.now().strftime("%H:%M:%S")))
########################################################################################################################

# Update value table to include eo reps geometery object instead of eo ptreps XY coordinates
srows = arcpy.da.SearchCursor(eo_shape, ["EO_ID", "SHAPE@"])
for srow in srows:
    # Create variable for search cursor (eo shape) EO ID
    eoid = srow[0]
    # Look up the corresponding record in the eor value table
    for row in eor_values:
        if row[1] == eoid:
            # Replace the last item in the row with the geometry object for eo reps
            row[-1] = srow[1]
            break

# Update field list to geometry object token instead of XY coordinates
eor_fields[-1] = "SHAPE@"
# Create eo reps
arcpy.CreateFeatureclass_management(pace_gdb, "eo_lyr", "POLYGON")
eo_reps = os.path.join(pace_gdb, "eo_lyr")
# Add eor fields using function defined at top of script
add_eor_fields(eo_reps)
# Insert eor values using insert cursor
cursor = arcpy.da.InsertCursor(eo_reps, eor_fields)
for row in eor_values:
    try:
        # Catch records that have no geometry attribute
        # because there are records in the value table that are not in the shapefile
        if len(eor_fields) == 30 and len(row) == 29:
            # Skip those records
            pass
        else:
            cursor.insertRow(row)
    except:
        print("{0}: {1} Failed at {2}".format("EO ID", row[1], datetime.datetime.now().strftime("%H:%M:%S")))
        # Get traceback object
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        # Concate information together concerning th error into a message string
        pymsg = "PYTHON ERRORS:\nTraceback info:\n" + tbinfo + "\nError Info:\n" + str(sys.exc_info()[1])
        msgs = "ArcPy ERRORS:\n" + arcpy.GetMessages(2) + "\n"
        # Return python error messages
        print(pymsg)
        print(msgs)
del cursor

########################################################################################################################
print("Creating source lines at {}".format(datetime.datetime.now().strftime("%H:%M:%S")))
########################################################################################################################

# Loop through all feature classes in the in_path that start with "SOURCE_FEATURE_PRE"
for fc in arcpy.ListFeatureClasses("SOURCE_FEATURE_PRE*"):
    # Create variables for pre source layers
    if "PRE_LINE" in fc:
        pre_line = fc
    elif "PRE_PT" in fc:
        pre_pt = fc
    elif "PRE_POLY" in fc:
        pre_poly = fc
    else:
        print('{} does not contain "PRE_LINE", "PRE_PT", or "PRE_POLY"'.format(fc))

# Create source lines
arcpy.CreateFeatureclass_management(pace_gdb, "eos_ln_lyr", "POLYLINE")
# Create variable to hold fullpathname of source lines
src_ln = os.path.join(pace_gdb, "eos_ln_lyr")
# Add sf fields using function defined at top of script
add_sf_fields(src_ln)

# ---- Get geometery from shapefile and attributes from value table, then create new feature using insert cursor
# Use insert cursor to insert new features into the new feature class
cursor = arcpy.da.InsertCursor(src_ln, sf_fields)
# Use search cursor to get geometry from the shapefile
srows = arcpy.da.SearchCursor(pre_line, ["SOURCE_FEA", "SHAPE@"])
for srow in srows:
    # Create variable for search cursor (pre_line) SF ID
    sfid = srow[0]
    # Create variable for geometry
    geo = srow[1]
    # Look up the corresponding record in the sf value table
    for row in sf_values:
        if row[4] == sfid:
            # Add geometry object to end of the row
            row.append(geo)
            # Insert row into new feature class
            try:
                cursor.insertRow(row)
            except:
                print("{0}: {1} Failed at {2}".format("SF ID", row[4], datetime.datetime.now().strftime("%H:%M:%S")))
                # Get traceback object
                tb = sys.exc_info()[2]
                tbinfo = traceback.format_tb(tb)[0]
                # Concate information together concerning th error into a message string
                pymsg = "PYTHON ERRORS:\nTraceback info:\n" + tbinfo + "\nError Info:\n" + str(sys.exc_info()[1])
                msgs = "ArcPy ERRORS:\n" + arcpy.GetMessages(2) + "\n"
                # Return python error messages
                print(pymsg)
                print(msgs)
                print
            break
del cursor

########################################################################################################################
print("Creating source polygons at {}".format(datetime.datetime.now().strftime("%H:%M:%S")))
########################################################################################################################

# Create source polygons
arcpy.CreateFeatureclass_management(pace_gdb, "eos_poly_lyr", "POLYGON")
# Create variable to hold fullpathname of source polygons
src_py = os.path.join(pace_gdb, "eos_poly_lyr")
# Add sf fields using function defined at top of script
add_sf_fields(src_py)

# ---- Get geometery from shapefile and attributes from value table, then create new feature using insert cursor
# Use insert cursor to insert new features into the new feature class
cursor = arcpy.da.InsertCursor(src_py, sf_fields)
# Use search cursor to get geometry from the shapefile
srows = arcpy.da.SearchCursor(pre_poly, ["SOURCE_FEA", "SHAPE@"])
for srow in srows:
    # Create variable for search cursor SF ID
    sfid = srow[0]
    # Create variable for geometry
    geo = srow[1]
    # Look up the corresponding record in the sf value table
    for row in sf_values:
        if row[4] == sfid:
            # Add geometry object to end of the row
            row.append(geo)
            # Insert row into new feature class
            try:
                cursor.insertRow(row)
            except:
                print("{0}: {1} Failed at {2}".format("SF ID", row[4], datetime.datetime.now().strftime("%H:%M:%S")))
                # Get traceback object
                tb = sys.exc_info()[2]
                tbinfo = traceback.format_tb(tb)[0]
                # Concate information together concerning th error into a message string
                pymsg = "PYTHON ERRORS:\nTraceback info:\n" + tbinfo + "\nError Info:\n" + str(sys.exc_info()[1])
                msgs = "ArcPy ERRORS:\n" + arcpy.GetMessages(2) + "\n"
                # Return python error messages
                print(pymsg)
                print(msgs)
            break
del cursor

########################################################################################################################
print("Creating source points at {}".format(datetime.datetime.now().strftime("%H:%M:%S")))
########################################################################################################################

# Replace geometry token in the list of fields with token for XY coordinates
sf_fields[-1] = "SHAPE@XY"
# Add latitude and longitude to sf fields
sf_fields.append("LAT")
sf_fields.append("LONG")

# Create source points
arcpy.CreateFeatureclass_management(pace_gdb, "eos_pt_lyr", "POINT")
# Create variable to hold fullpathname of source points
src_pt = os.path.join(pace_gdb, "eos_pt_lyr")
# Add sf fields using function defined at top of script
add_sf_fields(src_pt)
# Add latitude and longitude fields to source points
arcpy.AddField_management(src_pt, "LAT", "DOUBLE")
arcpy.AddField_management(src_pt, "LONG", "DOUBLE")

# ---- Get geometery from shapefile and attributes from value table, then create new feature using insert cursor
# Use insert cursor to insert new features into the new feature class
cursor = arcpy.da.InsertCursor(src_pt, sf_fields)
# Use search cursor to get geometry from the shapefile
srows = arcpy.da.SearchCursor(pre_pt, ["SOURCE_FEA", "SHAPE@XY"])
for srow in srows:
    # Create variable for search cursor SF ID
    sfid = srow[0]
    # Create variable for geometry
    geo = srow[1]
    # Look up the corresponding record in the sf value table
    for row in sf_values:
        if row[4] == sfid:
            # Add geometry object to end of the row
            row.append(geo)
            # Append Y coordinates to row to populate latitude field
            row.append(srow[1][1])
            # Append X coordinates to row to populate longitude field
            row.append(srow[1][0])
            # Insert row into new feature class
            try:
                cursor.insertRow(row)
            except:
                print("{0}: {1} Failed at {2}".format("SF ID", row[4], datetime.datetime.now().strftime("%H:%M:%S")))
                # Get traceback object
                tb = sys.exc_info()[2]
                tbinfo = traceback.format_tb(tb)[0]
                # Concate information together concerning th error into a message string
                pymsg = "PYTHON ERRORS:\nTraceback info:\n" + tbinfo + "\nError Info:\n" + str(sys.exc_info()[1])
                msgs = "ArcPy ERRORS:\n" + arcpy.GetMessages(2) + "\n"
                # Return python error messages
                print(pymsg)
                print(msgs)
            break
del cursor

########################################################################################################################
print("Projecting data to Bureau of Forestry projection at {}".format(datetime.datetime.now().strftime("%H:%M:%S")))
########################################################################################################################

in_gdb = os.path.join(out_path, gdb_name_albers)
out_gdb = os.path.join(out_path, gdb_name)

# Define workspace
arcpy.env.workspace = in_gdb

# Create new geodatabase to hold re-projected feature classes
# If it already exists, delete it
if os.path.exists(out_gdb):
    shutil.rmtree(out_gdb)
# Create HGIS Biotics geodatabase
arcpy.CreateFileGDB_management(out_path, gdb_name)

# List feature classes in gdb
fcs = arcpy.ListFeatureClasses()
for fc in fcs:
    out_fc = os.path.join(out_gdb, fc)
    try:
        print("\tProjecting {}".format(fc))
        arcpy.Project_management(fc, out_fc, bof_spatial_ref)
    except:
        # Get traceback object
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        # Concate information together concerning th error into a message string
        pymsg = "PYTHON ERRORS:\nTraceback info:\n" + tbinfo + "\nError Info:\n" + str(sys.exc_info()[1])
        msgs = "ArcPy ERRORS:\n" + arcpy.GetMessages(2) + "\n"
        # Return python error messages
        print(pymsg)
        print(msgs)

# Delete the albers version of the geodatabase
if os.path.exists(in_gdb):
    shutil.rmtree(in_gdb)

########################################################################################################################
print("Completed script at {}".format(datetime.datetime.now().strftime("%H:%M:%S")))
########################################################################################################################
