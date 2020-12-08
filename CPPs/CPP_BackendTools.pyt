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
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        cpp_eo_reps = arcpy.Parameter(
            displayName = "CPP EO Reps Layer",
            name = "cpp_eo_reps",
            datatype = "GPFeatureLayer",
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
        arcpy.SelectLayerByAttribute_management(cpp_lyr,"NEW_SELECTION","{} <> 'n' AND {} IS NULL".format(status_field,null_field))
        oid_field = arcpy.Describe(cpp_lyr).OIDFieldName
        with arcpy.da.SearchCursor(cpp_lyr,oid_field) as cursor:
            oids = sorted({row[0] for row in cursor})
        arcpy.RemoveJoin_management(cpp_lyr)
        arcpy.AddMessage(str(len(oids)))

        desc = arcpy.Describe(cpp_lyr)
        workspace = os.path.dirname(desc.path)

        arcpy.AddMessage(workspace)

        edit = arcpy.da.Editor(workspace)

        oid_field = arcpy.Describe(cpp_lyr).OIDFieldName
        t = date.today()
        d = t.strftime('%m/%d/%Y')

        edit.startEditing(False,True)
        edit.startOperation()
        with arcpy.da.UpdateCursor(cpp_lyr,[oid_field,"Status","ReviewBy","ReviewDate","ReviewNotes"]) as cursor:
            for row in cursor:
                if row[0] in oids:
                    arcpy.AddMessage(str(row[0]))
                    row[1] = "n"
                    row[2] = "mmoore"
                    row[3] = d
                    row[4] = "CPP no longer meets age, tracking, or accuracy criteria."
                    cursor.updateRow(row)
                else:
                    pass
        edit.stopOperation()
        edit.stopEditing(True)