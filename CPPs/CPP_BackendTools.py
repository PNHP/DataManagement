#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      MMoore
#
# Created:     18/09/2020
# Copyright:   (c) MMoore 2020
# Licence:     <your licence>
#-------------------------------------------------------------------------------

# import system modules
import arcpy, os, datetime
from datetime import date

# Set tools to overwrite existing outputs
arcpy.env.overwriteOutput = True

######################################################################################################################################################
## Begin toolbox
######################################################################################################################################################

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the .pyt file)."""
        self.label = "CPP Backend Tools"
        self.alias = "CPP Backend Tools"
        self.canRunInBackground = False
        self.tools = [CPPcriteria]

######################################################################################################################################################
## Begin create NHA tool - this tool creates the core and supporting NHAs and fills their initial attributes
######################################################################################################################################################

class CPPcriteria(object):
    def __init__(self):
        self.label = "Update CPPs that no longer meet criteria"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        cpp_layer = arcpy.Parameter(
            displayName = "CPP Layer to be updated",
            name = "cpp_layer",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input")

        cpp_eo_reps = arcpy.Parameter(
            displayName = "CPP EO Reps Layer",
            name = "cpp_eo_reps",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input")

        params = [cpp_layer,cpp_eo_reps]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, params):
        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):

        cpp_layer = params[0].valueAsText
        cpp_eo_reps = params[1].valueAsText

        cpp_lyr = arcpy.MakeFeatureLayer_management(cpp_layer,"cpp_lyr")
        cpp_eo_reps_lyr = arcpy.MakeFeatureLayer_management(cpp_eo_reps,"cpp_eo_reps_lyr")

        arcpy.AddJoin_management(cpp_lyr,"EO_ID",cpp_eo_reps,"EO_ID","KEEP_ALL")

        status_field = os.path.basename(cpp_layer)+".Status"
        null_field = os.path.basename(cpp_eo_reps)+".EO_ID"
        reviewby_field = os.path.basename(cpp_layer)+".ReviewBy"
        reviewdate_field = os.path.basename(cpp_layer)+".ReviewDate"
        reviewnotes_field = os.path.basename(cpp_layer)+".ReviewNotes"
        arcpy.SelectLayerByAttribute_management(cpp_lyr,"NEW_SELECTION","{} <> 'n' AND {} IS NULL".format(status_field,null_field))

        today = date.today()
        date = today.strfttime('%d/%m/%Y')
        with arcpy.da.UpdateCursor(cpp_lyr,[reviewby_field,reviewdate_field,reviewnotes_field]) as cursor:
            for row in cursor:
                row[0] = "mmoore"
                row[1] = date
                row[2] = "Not approved because CPP no longer meets age, tracking, or accuracy criteria"
                cursor.updateRow(row)
