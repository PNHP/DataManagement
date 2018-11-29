#-------------------------------------------------------------------------------
# Name:        CPP Identical EO Selector
# Purpose:     Selects CPP records with duplicate EOs. This script should be run
#              within ArcGIS Python window because it uses feature layers. Steps
#              for running script in ArcMap:
#              1. open new or existing ArcMap document and add CPP layer in which you wish to find duplicates to the active data frame
#              2. open the Python window within ArcMap (--> Geoprocessing --> Python)
#              3. copy and paste this code into the Python window and press enter
#              4. type selectIdentical('<cpp layer name>') into the Python window, replace <cpp layer name> with the name of the cpp layer in your active data frame (you can also drag and drop the file from the active data frame), and press enter to run the script
#              5. once the script finishes, open your cpp layer within which you wanted to find duplicates and all records that have duplicate EO IDs will be highlighted
#              6. if you click the 'show selected records' button and sort by EO ID, you will be able to see duplicates beside one another
# Author:      Molly Moore
# Created:     2017-02-20
# Updated:
#
# To Do List/Future ideas:
#
#-------------------------------------------------------------------------------

# import system modules
import arcpy, os, datetime
from arcpy import env
from arcpy.sa import *

# Set tools to overwrite existing outputs
arcpy.env.overwriteOutput = True

def selectIdentical(dataset):
    dups = os.path.join("in_memory", "tempDups")
    dups1 = arcpy.FindIdentical_management(dataset, dups, 'EO_ID', output_record_option = "ONLY_DUPLICATES")

    with arcpy.da.SearchCursor(dups1, 'IN_FID') as cursor:
        duplicates = sorted({row[0] for row in cursor})

    query = '"OBJECTID" IN ' + str(tuple(duplicates))

    arcpy.SelectLayerByAttribute_management(dataset, "ADD_TO_SELECTION", query)