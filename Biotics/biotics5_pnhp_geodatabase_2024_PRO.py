"""
Name: Biotics5 Monthly Data Packaging - PNHP File Geodatabase
Purpose: This script creates the PNHP file geodatabase containing the Biotics feature classes for CPP, NHA, and biologist use.

Author: K. Erath
Created: 2014-04-17, updated 2024-11-25 for use with Python 3 and Pro license
Updates:
2016-07-25: SK added EO_Rule to EO feature classes
2022-04-20: SK added NHA fields
2024-11-18: SK added Visit Years fields to SF
2024-11-26: MMoore updated for use with Python 3 and Pro license, updated projection info to use string instead of needing connection to Favorites folder.
"""

# Import modules
import arcpy
import os
import sys
import shutil
import traceback
import time
import datetime
import sched
import glob
import zipfile
import gc

# Set environment variables and defaults
arcpy.env.overwriteOutput = True

# define projections
# define custom albers projection and assign it to output coordinate system environment variable
albers_str = r'PROJCS["alber",GEOGCS["GCS_North_American_1983",DATUM["D_North_American_1983",SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Albers"],PARAMETER["false_easting",0.0],PARAMETER["false_northing",0.0],PARAMETER["central_meridian",-78.0],PARAMETER["standard_parallel_1",40.0],PARAMETER["standard_parallel_2",42.0],PARAMETER["latitude_of_origin",39.0],UNIT["Meter",1.0]];-16085300 -8515400 10000;0 1;0 1;0.001;0.001;0.001;IsHighPrecision'
albers_prj = arcpy.SpatialReference()
albers_prj.loadFromString(albers_str)
arcpy.env.outputCoordinateSystem = albers_prj

########################################################################################################################
# SET THESE PATH NAMES TO THE CORRECT PATH NAMES ON YOUR LOCAL COMPUTER
########################################################################################################################
# Update these to your input and output paths
# The input path should be a folder that contains this month's exported zip files (shapefiles) and the export views.
# The input path CANNOT contain the previous months exports
in_path = r"H:\temp\Biotics_export_testing\20241115"
w_out_path = r"H:\temp\Biotics_export_testing\20241115\gdb"
gdb_name = "Biotics_datasets.gdb"

########################################################################################################################
# END PATH NAME CHANGES
########################################################################################################################


# Variable for final geodatabase
biotics_gdb = os.path.join(in_path, gdb_name)

# EOR fields for insert cursor
eor_fields = ["EO_ID","ELCODE","EO_NUM","SNAME","SCOMNAME","ELSUBID","ID_CONFIRM", "LASTOBS","LASTOBS_YR","SURVEYDATE",
              "SURVEY_YR","EO_TRACK","GRANK","SRANK","SPROT","USESA","PBSSTATUS","PBSQUAL","SGCN","SENSITV_SP",
              "SENSITV_EO","EO_TYPE","NUM_SF","SITE_NAME","SURVEYSITE","EO_DATA","GEN_DESC","GENERL_COM","EORANK",
              "EORANKCOM","CONDITION","EO_SIZE","LANDSCP","MGMT_COM","PROT_COM","PREC_BCD","EST_RA","QUAD_FILE",
              "ER_RULE","EO_RULE","X","Y","LEAD_RESP","MOD_BY","MOD_DATE","MAPPEDBY","MAPPEDDATE","EXPT_DATE","SHAPE@"]

# SF fields for insert cursor
sf_fields = ["SF_ID","EO_ID","ELCODE","SNAME","SCOMNAME","ELSUBID","SF_DESCRIP","SF_LOCATOR","VISITS","GRANK","SRANK",
             "USESA","SPROT","PBSSTATUS","EO_TRACK","C_FEAT_TYPE","LU_TYPE","LU_DIST","LU_UNIT","USE_CLASS","DIGI_COM",
             "MAP_COM","INDEP_SF","EST_RA","MAPPED_BY","MAPPEDDATE","MOD_BY","MOD_DATE","EXPT_DATE","SHAPE@"]


# Define functions
def add_eor_fields(in_fc):
    """Adds all Element Occurrence Records (EOR) fields to the input feature class, in_fc. This function is
    used to add fields to eo ptreps and eo reps."""
    arcpy.AddField_management(in_fc, "EO_ID", "LONG")
    arcpy.AddField_management(in_fc, "ELCODE", "TEXT", field_length=10)
    arcpy.AddField_management(in_fc, "EO_NUM", "SHORT")
    arcpy.AddField_management(in_fc, "SNAME", "TEXT", field_length=200, field_alias="SCIENTIFIC NAME")
    arcpy.AddField_management(in_fc, "SCOMNAME", "TEXT", field_length=400, field_alias="COMMON NAME")
    arcpy.AddField_management(in_fc, "ELSUBID", "LONG", field_alias="ELEMENT ID")
    arcpy.AddField_management(in_fc, "ID_CONFIRM", "TEXT", field_length=20)
    arcpy.AddField_management(in_fc, "LASTOBS", "TEXT", field_length=25, field_alias="LAST OBSERVED DATE")
    arcpy.AddField_management(in_fc, "LASTOBS_YR","LONG", field_alias="LAST OBSERVED YEAR")
    arcpy.AddField_management(in_fc, "SURVEYDATE", "TEXT", field_length=25, field_alias="LAST SURVEY DATE")
    arcpy.AddField_management(in_fc, "SURVEY_YR", "LONG", field_alias="LAST SURVEY YEAR")
    arcpy.AddField_management(in_fc, "EO_TRACK", "TEXT", field_length=5, field_alias="ELEMENT TRACKING STATUS")
    arcpy.AddField_management(in_fc, "GRANK", "TEXT", field_length=20)
    arcpy.AddField_management(in_fc, "SRANK", "TEXT", field_length=20)
    arcpy.AddField_management(in_fc, "SPROT", "TEXT", field_length=20, field_alias="STATE STATUS")
    arcpy.AddField_management(in_fc, "USESA", "TEXT", field_length=20, field_alias="FEDERAL STATUS")
    arcpy.AddField_management(in_fc, "PBSSTATUS", "TEXT", field_length=20)
    arcpy.AddField_management(in_fc, "PBSQUAL", "TEXT", field_length=2147483647)
    arcpy.AddField_management(in_fc, "SGCN", "TEXT", field_length=20)
    arcpy.AddField_management(in_fc, "SENSITV_SP", "TEXT", field_length=1, field_alias="SENSITIVE SPECIES")
    arcpy.AddField_management(in_fc, "SENSITV_EO", "TEXT", field_length=1, field_alias="SENSITIVE EO")
    arcpy.AddField_management(in_fc, "EO_TYPE", "TEXT", field_length=50)
    arcpy.AddField_management(in_fc, "NUM_SF", "LONG", field_alias="NUMBER OF SF")
    arcpy.AddField_management(in_fc, "SITE_NAME", "TEXT", field_length=2147483647, field_alias="SITE NAME (FORMAL)")
    arcpy.AddField_management(in_fc, "SURVEYSITE", "TEXT", field_length=2147483647)
    arcpy.AddField_management(in_fc, "EO_DATA", "TEXT", field_length=2147483647)
    arcpy.AddField_management(in_fc, "GEN_DESC", "TEXT", field_length=2147483647, field_alias="GENERAL DESCRIPTION")
    arcpy.AddField_management(in_fc, "GENERL_COM", "TEXT", field_length=2147483647, field_alias="GENERAL COMMENTS")
    arcpy.AddField_management(in_fc, "EORANK", "TEXT", field_length=5)
    arcpy.AddField_management(in_fc, "EORANKCOM", "TEXT", field_length=2147483647, field_alias="EORANK COMMENTS")
    arcpy.AddField_management(in_fc, "CONDITION", "TEXT", field_length=2147483647)
    arcpy.AddField_management(in_fc, "EO_SIZE", "TEXT", field_length=2147483647, field_alias="SIZE OF EO")
    arcpy.AddField_management(in_fc, "LANDSCP", "TEXT", field_length=2147483647, field_alias="LANDSCAPE CONTEXT")
    arcpy.AddField_management(in_fc, "MGMT_COM", "TEXT", field_length=2147483647, field_alias="MGMT COMMENTS")
    arcpy.AddField_management(in_fc, "PROT_COM", "TEXT", field_length=2147483647, field_alias="PROTECTION COMMENTS")
    arcpy.AddField_management(in_fc, "PREC_BCD", "TEXT", field_length=5, field_alias="PRECISION BCD")
    arcpy.AddField_management(in_fc, "EST_RA", "TEXT", field_length=20, field_alias="ESTIMATED REPRESENTATIONAL ACCURACY")
    arcpy.AddField_management(in_fc, "QUAD_FILE", "TEXT", field_length=2147483647, field_alias="FILING QUAD")
    arcpy.AddField_management(in_fc, "ER_RULE", "TEXT", field_length=10)
    arcpy.AddField_management(in_fc, "EO_RULE", "TEXT", field_length=50)
    arcpy.AddField_management(in_fc, "X", "FLOAT")
    arcpy.AddField_management(in_fc, "Y", "FLOAT")
    arcpy.AddField_management(in_fc, "LEAD_RESP", "TEXT", field_length=10)
    arcpy.AddField_management(in_fc, "MOD_BY", "TEXT", field_length=50)
    arcpy.AddField_management(in_fc, "MOD_DATE", "DATE")
    arcpy.AddField_management(in_fc, "MAPPEDBY", "TEXT", field_length=20)
    arcpy.AddField_management(in_fc, "MAPPEDDATE", "DATE")
    arcpy.AddField_management(in_fc, "EXPT_DATE", "DATE", field_alias="EXPORT DATE")


def add_sf_fields(in_fc):
    """Adds all Source Feature (SF) fields to the input feature class, in_fc. This function is
    used to add fields to source lines, points, and polygons."""
    arcpy.AddField_management(in_fc, "SF_ID", "LONG")
    arcpy.AddField_management(in_fc, "EO_ID", "LONG")
    arcpy.AddField_management(in_fc, "ELCODE", "TEXT", field_length=10)
    arcpy.AddField_management(in_fc, "SNAME", "TEXT", field_length=200, field_alias="SCIENTIFIC NAME")
    arcpy.AddField_management(in_fc, "SCOMNAME", "TEXT", field_length=400, field_alias="COMMON NAME")
    arcpy.AddField_management(in_fc, "ELSUBID", "LONG", field_alias="ELEMENT ID")
    arcpy.AddField_management(in_fc, "SF_DESCRIP", "TEXT", field_length=250, field_alias="SOURCE FEATURE DESCRIPTOR")
    arcpy.AddField_management(in_fc, "SF_LOCATOR", "TEXT", field_length=500, field_alias="SOURCE FEATURE LOCATOR")
    arcpy.AddField_management(in_fc, "VISITS", "TEXT", field_length=2147483647)
    arcpy.AddField_management(in_fc, "GRANK", "TEXT", field_length=20)
    arcpy.AddField_management(in_fc, "SRANK", "TEXT", field_length=20)
    arcpy.AddField_management(in_fc, "USESA", "TEXT", field_length=20, field_alias="FEDERAL STATUS")
    arcpy.AddField_management(in_fc, "SPROT", "TEXT", field_length=50, field_alias="STATE STATUS")
    arcpy.AddField_management(in_fc, "PBSSTATUS", "TEXT", field_length=10)
    arcpy.AddField_management(in_fc, "EO_TRACK", "TEXT", field_length=10, field_alias="ELEMENT TRACKING STATUS")
    arcpy.AddField_management(in_fc, "C_FEAT_TYPE", "TEXT", field_length=20, field_alias="CONCEPTUAL FEATURE TYPE")
    arcpy.AddField_management(in_fc, "LU_TYPE", "TEXT", field_length=20, field_alias="LOCATIONAL UNCERTAINTY TYPE")
    arcpy.AddField_management(in_fc, "LU_DIST", "FLOAT", field_alias="LOCATIONAL UNCERTAINTY DISTANCE")
    arcpy.AddField_management(in_fc, "LU_UNIT", "TEXT", field_length=20, field_alias="LOCATIONAL UNCERTAINTY UNIT")
    arcpy.AddField_management(in_fc, "USE_CLASS", "TEXT", field_length=50, field_alias="LOCATION USE CLASS")
    arcpy.AddField_management(in_fc, "DIGI_COM", "TEXT", field_length=2147483647, field_alias="DIGITIZING COMMENTS")
    arcpy.AddField_management(in_fc, "MAP_COM", "TEXT", field_length=2147483647, field_alias="MAPPING COMMENTS")
    arcpy.AddField_management(in_fc, "INDEP_SF", "TEXT", field_length=1, field_alias="INDEPENDENT SOURCE FEATURE")
    arcpy.AddField_management(in_fc, "EST_RA", "TEXT", field_length=20, field_alias="ESTIMATED REPRESENTATIONAL ACCURACY")
    arcpy.AddField_management(in_fc, "MAPPED_BY", "TEXT", field_length=25)
    arcpy.AddField_management(in_fc, "MAPPEDDATE", "DATE")
    arcpy.AddField_management(in_fc, "MOD_BY", "TEXT", field_length=50)
    arcpy.AddField_management(in_fc, "MOD_DATE", "DATE")
    arcpy.AddField_management(in_fc, "EXPT_DATE", "DATE", field_alias="EXPORT DATE")
    arcpy.AddField_management(in_fc, "MAX_VISIT_YR", "SHORT", field_alias="MAX_VISIT_YR")
    arcpy.AddField_management(in_fc, "MAX_DET_YR", "SHORT", field_alias="MAX_DETECTED_YR")



def excel_to_value_table(biotics_or_hgis, work_gdb, eo_or_sf):
    """Loops through Excel tables, using hgis or biotics wildcard, in the in_path.
    Converts Excel tables to GIS tables. Builds value table based on attributes
    in GIS tables. Returns eo or sf value table."""
    wildcard = "{0}_{1}*.xlsx".format(biotics_or_hgis, eo_or_sf)
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
        ''' Note about why ExcelToTable tool was used:
        Accessing csv directly via csv module -> Unicode errors
        MakeTableView -> Long text fields came out null or were skipped
        TableToTable tool -> Truncated long text fields to 254 even with geodatabase table as output
        Addtional Note:'''
    #---- Loop through newly created GIS tables and create value table
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
    '''
    Note why script loops through GIS tables instead of merging into 1 GIS table:
    When converting Excel to GIS, the GIS text field will be the minimum it needs to be for that Excel table. If a
    preceding GIS table in the Merge has a shorter max text length then the next, the tool will fail.
    '''
    # Set the workspace back to in_path
    arcpy.env.workspace = in_path
    return value_table

def create_biotics_file(in_fc, out_fc_name, fc_shape, eo_or_sf):
    """This function creates a new feature class and adds the necessary fields. The geometry is retrieved from the
    appropriate shapefile and the rest of the attributes come from the value table. The new feature class is named
    out_fc_name in the Biotics geodatabase. The geometry of the new feature class is determined by the fc_shape
    parameter and should be POINT, POLYLINE, or POLYGON. eo_or_sf determines the which field function, list of fields,
    value table, and id field to use."""
    # Set variables based on parameters
    if eo_or_sf == "eo":
        fields_function = add_eor_fields
        fields_list = eor_fields
        value_table = eor_values
        shape_id_field = "EO_ID"
    if eo_or_sf == "sf":
        fields_function = add_sf_fields
        fields_list = sf_fields
        value_table = sf_values
        shape_id_field = "SOURCE_FEA"
    if fc_shape == "POINT":
        gtoken = "SHAPE@XY"
    else:
        gtoken = "SHAPE@"

    print("Creating {0} from {2} at {1}".format(out_fc_name, datetime.datetime.now().strftime("%H:%M:%S"), in_fc))
    # Create feature class
    arcpy.CreateFeatureclass_management(biotics_gdb, out_fc_name, fc_shape)
    # Create variable for full pathname of new feature class
    out_fc = os.path.join(biotics_gdb, out_fc_name)
    # Add fields to new feature class
    fields_function(out_fc)

    #---- Get geometery from shapefile and attributes from value table, then create new feature using insert cursor
    # Use insert cursor to insert new features into the new feature class
    cursor = arcpy.da.InsertCursor(out_fc, fields_list)
    # Use search cursor to get geometry from the shapefile
    srows = arcpy.da.SearchCursor(in_fc, [shape_id_field, gtoken])
    # Make sure the fields list has the correct geometry token
    fields_list[-1] = gtoken
    for srow in srows:
        # Create variable for search cursor ID
        uid = srow[0]
        # Create variable for geometry
        geom = srow[1]
        # Look up the corresponding record in the value table
        for row in value_table:
            if row[0] == uid:
                # Add geometry object to end of the row
                row.append(geom)
                # Insert row into new feature class
                try:
                    cursor.insertRow(row)
                except:
                    print
                    print("{0}: {1} Failed at {2}".format(shape_id_field, uid, datetime.datetime.now().strftime("%H:%M:%S")))
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

def check_locks_gdb(gdb):
    """This function checks for lock files in a geodatabase (or any directory).
    If there is a lock file, the script pauses for 30 mins and checks again. The
    function will exit when there are no lock files in the geodatabase."""
    # Define function that does nothing
    def void():
        pass

    # Set count to 1 so script will enter while loop
    count = 1
    while count >= 1:
        # Set count back to 0
        count = 0
        # Loop through files in the geodatabase
        for filename in os.listdir(gdb):
            # Check for lock files
            if filename.endswith('.lock'):
                # If there is a lock file, increase the count
                count +=1
                # Print the name of the lock file
                print("\tLocked file:", filename)
            else:
                pass
        print("\tThere are {} LOCK file(s) in the geodatabase.".format(count))
        if count >=1:
            print("\tPausing script for 30min")
            # Pause script for 30 min and run function that does nothing
##            s.enter(1800, 1, void, ())
            sys.exit()
            s.run()

def replace_gdb(in_gdb, out_gdb):
    """This function replaces the out_gdb with the in_gdb."""
    # Check to see if geodatabase exists
    if os.path.exists(out_gdb):

        # Check for geodatabase schema locks
        print("\tChecking for locks on {}".format(out_gdb))
        check_locks_gdb(out_gdb)

        # Delete old geodatabase
        print("\tDeleting {0}".format(out_gdb, datetime.datetime.now().strftime("%H:%M:%S")))
        shutil.rmtree(out_gdb)

    # Copy input geodatabse to output geodatabase
    print("\tCopying {0}".format(in_gdb, datetime.datetime.now().strftime("%H:%M:%S")))
    shutil.copytree(in_gdb, out_gdb)

    print("\tReplacement complete for {}".format(out_gdb))


########################################################################################################################
print("Starting script at {}".format(datetime.datetime.now().strftime("%H:%M:%S")))
########################################################################################################################

# Set environment workspace
arcpy.env.workspace = in_path

# Extract all zip files in the in_path
path = "{}//*.zip".format(in_path)
for fname in glob.glob(path):
    with zipfile.ZipFile(fname, 'r') as myzip:
        myzip.extractall(in_path)

########################################################################################################################
print("Creating Biotics geodatabase at {}".format(datetime.datetime.now().strftime("%H:%M:%S")))
########################################################################################################################

#---- Create Biotics geodatabase
# If it already exists, delete it
if os.path.exists(biotics_gdb):
    shutil.rmtree(biotics_gdb)
# Create Biotics geodatabase
arcpy.CreateFileGDB_management(in_path, gdb_name)

########################################################################################################################
print("Getting attributes from EO and SF table views at {}".format(datetime.datetime.now().strftime("%H:%M:%S")))
########################################################################################################################

eor_values = excel_to_value_table("biotics", biotics_gdb, "eo")
sf_values = excel_to_value_table("biotics", biotics_gdb, "sf")

########################################################################################################################
print("Creating eo reps at {}".format(datetime.datetime.now().strftime("%H:%M:%S")))
########################################################################################################################

# Create variable for eo shape, using star wildcard to grab the file that starts with EO_SHAPE
for f in arcpy.ListFeatureClasses("EO_SHAPE*"):
        eo_shape = f

# Create eo reps using create_biotics_file function defined at the top of the script
create_biotics_file(eo_shape, "eo_reps", "POLYGON", "eo")

########################################################################################################################
print("Creating eo ptreps at {}".format(datetime.datetime.now().strftime("%H:%M:%S")))
########################################################################################################################

# Loop through eo value table and replace geometry
for row in eor_values:
    # Replace geometry object with xy coordinates contained in the x and y fields
    # CHECK THIS LINE IF CHANGING LISTS OF FIELDS
    # NEED TO ADJUST FOR CHANGE IN LOCATION OF X AND Y COORDS IN EO FIELDS LIST
    # X AND Y NUMBERS ARE ROW NUM IN ABOVE LIST MINUS 1
    row[-1] = (row[40],row[41])

# Change last field in eo fields to xy coordinates instead of whole geometry object
eor_fields[-1] = "SHAPE@XY"

# Create variable to hold full pathname of eo ptreps
eo_ptreps = os.path.join(biotics_gdb,"eo_ptreps")
# Create eo ptreps
arcpy.CreateFeatureclass_management(biotics_gdb, "eo_ptreps", "POINT")
# Add eor fields using function defined at top of script
add_eor_fields(eo_ptreps)
# Insert eor values using insert cursor
cursor = arcpy.da.InsertCursor(eo_ptreps, eor_fields)
for row in eor_values:
    try:
        # Catch records that have no geometry attribute
        # because there are records in the value table that are not in the shapefile
        # This step must be updated any time fields are added to or deleted from the eo table
        if len(eor_fields) == 49 and len(row) == 48:
            # Skip those records
            pass
        else:
            cursor.insertRow(row)
    except:
        print("{0}: {1} Failed at {2}".format("EO_ID", row[0], datetime.datetime.now().strftime("%H:%M:%S")))
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
del cursor

########################################################################################################################
print("Creating source features at {}".format(datetime.datetime.now().strftime("%H:%M:%S")))
########################################################################################################################

# Loop through all feature classes in the in_path that start with "SOURCE_FEATURE_PRE"
# and create new source feature feature classes
for fc in arcpy.ListFeatureClasses("SOURCE_FEATURE_PRE*"):
    if "PRE_LINE" in fc:
        # Create eo sourceln using create_biotics_file function defined at the top of the script
        create_biotics_file(fc, "eo_sourceln", "POLYLINE", "sf")
    elif "PRE_PT" in fc:
        # Create eo sourcept using create_biotics_file function defined at the top of the script
        create_biotics_file(fc, "eo_sourcept", "POINT", "sf")
    elif "PRE_POLY" in fc:
        # Create eo sourcepy using create_biotics_file function defined at the top of the script
        create_biotics_file(fc, "eo_sourcepy", "POLYGON", "sf")

########################################################################################################################
print("Copying Biotics database to the W:\ drive at {}".format(datetime.datetime.now().strftime("%H:%M:%S")))
########################################################################################################################

in_gdb = os.path.join(in_path, gdb_name)
out_gdb = os.path.join(w_out_path, gdb_name)

"""This block of code is commented out because the import metadata tools leave locks
that persist after the tool has completed. The lock files prevent the geodatabase
from being copied. If metadata needs to be copied, uncomment this block and comment
out the copy geodatabase block. Run the copy geodatabase script separately. You may
need to close PyScripter and reopen it before running the copy geodatabase script)."""
###---- Copy metadata from previous months files
### If the out_gdb already exists
##if os.path.exists(out_gdb):
##    # Set the workspace to the output geodatabase
##    arcpy.env.workspace = out_gdb
##    # Loop though the feature classes in the output geodatabase and copy the metadata
##    fcs = arcpy.ListFeatureClasses()
##    for fc in fcs:
##        print "\tImporting metadata:", fc
##        source = r"{0}\{1}".format(out_gdb, fc)
##        target = r"{0}\{1}".format(in_gdb, fc)
##        # Copy the metadata of the feature class
##        arcpy.MetadataImporter_conversion(source, target) # Leaves locks on output geodatabase until PyScripter window is closed
##    # Copy the metadata of the geodatabase
##    arcpy.MetadataImporter_conversion(out_gdb, in_gdb) # Leaves locks on output geodatabase until PyScripter window is closed

#---- Copy geodatabase from in_path to the folder on the W: drive
# Create instance of scheduler class
s = sched.scheduler(time.time, time.sleep)
# Check that you are connected to the network
if os.path.exists(w_out_path):
    print("\tYou are connected to the network. Proceeding with script.")
else:
    print("Check network connection")
    sys.exit("Could not find {}".format(w_out_path))
# Run function to replace the geodatabase

replace_gdb(in_gdb, out_gdb)

########################################################################################################################
print("Completed script at {}".format(datetime.datetime.now().strftime("%H:%M:%S")))
########################################################################################################################

