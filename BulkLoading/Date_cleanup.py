#-------------------------------------------------------------------------------
# Name:        Date Field Cleanup
# Purpose:     This script manipulates date fields so that 12:00:00 PM is added
#              to the date ensuring the correct date to be displayed in ArcGIS
#              online despite time zone issues.
# Author:      Molly Moore
# Created:     2017-02-15
# Updated:
#
# To Do List/Future ideas:
#
#-------------------------------------------------------------------------------

################################################################################
## SET THESE VARIABLES
################################################################################

# database that contains the feature classes to be modified
database = arcpy.GetParameterAsText(0) # use this for arc tool
#database = r'Database Connections\FIND3.mmoore.pgh-gis.sde' # use this for standalone Python script and change to database that contains feature classes to be edited

# input_features should include list of feature classes to be modified
input_features = arcpy.GetParameterAsText(1) # use this for arc tool
#input_features = ["FIND3.DBO.el_pt", "FIND3.DBO.el_line", "FIND3.DBO.comm_poly","FIND3.DBO.comm_pt", "FIND3.DBO.el_poly", "FIND3.DBO.survey_poly"] # use this for standalone Python script and change to the feature classes to be edited

#fields to be edited
edit_fields = arcpy.GetParameterAsText(2) # use this for arc tool
#edit_fields = [] # use this for standalone Python script and change to the fields to be edited

################################################################################
## START SCRIPT
################################################################################

# import system modules
import arcpy, os, datetime
from arcpy import env
from arcpy.sa import *

# Set tools to overwrite existing outputs
arcpy.env.overwriteOutput = True

# begin editing session within database
edit = arcpy.da.Editor(database)
edit.startEditing(False, True)
edit.startOperation()

# begin loop for all input feature classes
for feature in input_features:
    # begin loop for all fields to be edited
    for field in edit_fields:
        # create cursor to loop through all records in edit fields within feature
        with arcpy.da.UpdateCursor(os.path.join(database, feature), field) as cursor:
            for row in cursor:
                # if field is null, do nothing
                if row[0] == None:
                    pass
                else:
                    value = str(row[0])
                    update = value.split(' ', 2)[0]
                    update = update + ' 12:00:00 PM'
                    row[0] = update
                    cursor.updateRow(row)

del cursor
edit.stopOperation()
edit.stopEditing(True)

