#-------------------------------------------------------------------------------
# Name:        FIND Database Cleanup
# Purpose:     This script is to be run periodically to clean up attributes
#              entered into the FIND database. Currently, the FIND Database
#              Script does the following:
#              1. removes white space from reference codes
#              2. makes all characters in reference codes upper case
#              3. removes default time from 'start_date' and 'end_date' fields
#              4. adds 12:00:00 PM to 'start_date' and 'end_date' fields
#              5. changes any null values in 'dm_stat' field to 'draft'
# Author:      Molly Moore
# Created:     2017-02-13
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

workspace = r"C:\Users\mmoore\AppData\Roaming\ESRI\Desktop10.6\ArcCatalog\FIND.Working.pgh-gis0.sde"
el_pt = r'{}\FIND.DBO.el_pt'.format(workspace)
el_line = r'{}\FIND.DBO.el_line'.format(workspace)
comm_poly = r'{}\FIND.DBO.comm_poly'.format(workspace)
comm_pt = r'{}\FIND.DBO.comm_pt'.format(workspace)
el_poly = r'{}\FIND.DBO.el_poly'.format(workspace)
survey_poly = r'{}\FIND.DBO.survey_poly'.format(workspace)

input_features = [el_pt, el_line, comm_poly, comm_pt, el_poly, survey_poly]
edit = arcpy.da.Editor(workspace)
edit.startEditing(True, True)
edit.startOperation()


for feature in input_features:
    with arcpy.da.UpdateCursor(feature, ['dm_stat', 'refcode']) as cursor:
        for row in cursor:
            if row[0] == None or row[0] == "" or row[0] == " ":
                row[0] = 'dr'
                cursor.updateRow(row)
            if row[1] == None:
                pass
            else:
                update = str(row[1]).replace(' ', '')
                update = update.upper()
                if row[1] != update:
                    row[1] = update
                    cursor.updateRow(row)

for feature in input_features[0:5]:
    with arcpy.da.UpdateCursor(feature, ['date_start', 'date_stop']) as cursor:
        for row in cursor:
            if row[0] == None:
                pass
            elif '12:00:00' in str(row[0]):
                pass
            else:
                value = str(row[0])
                update = value.split(' ', 2)[0]
                update = update + ' 12:00:00 PM'
                row[0] = update
                cursor.updateRow(row)

            if row[1] == None:
                pass
            elif '12:00:00' in str(row[1]):
                pass
            else:
                value = str(row[1])
                update = value.split(' ', 2)[0]
                update = update + ' 12:00:00 PM'
                row[1] = update
                cursor.updateRow(row)

with arcpy.da.UpdateCursor(survey_poly, ['survey_start', 'survey_end']) as cursor:
    for row in cursor:
        if row[0] == None:
            pass
        elif '12:00:00' in str(row[0]):
            pass
        else:
            value = str(row[0])
            update = value.split(' ', 2)[0]
            update = update + ' 12:00:00 PM'
            row[0] = update
            cursor.updateRow(row)

        if row[1] == None:
            pass
        elif '12:00:00' in str(row[1]):
            pass
        else:
            value = str(row[1])
            update = value.split(' ', 2)[0]
            update = update + ' 12:00:00 PM'
            row[1] = update
            cursor.updateRow(row)

del cursor
edit.stopOperation()
edit.stopEditing(True)