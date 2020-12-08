#-------------------------------------------------------------------------------
# Name:        FIND Admin Tools
# Purpose:
# Author:      mmoore
# Created:     10/20/2020
#-------------------------------------------------------------------------------

######################################################################################################################################################
## Import packages and define environment settings
######################################################################################################################################################

import arcpy,time,datetime,os,sys,string
from getpass import getuser

arcpy.env.overwriteOutput = True

et = r"W:\\Heritage\\Heritage_Data\\Biotics_datasets.gdb\\ET"

######################################################################################################################################################
## Begin toolbox
######################################################################################################################################################

class Toolbox(object):
    def __init__(self):
        self.label = "FIND Admin Toolbox"
        self.alias = "FIND Admin Toolbox"
        self.tools = [DMReports]

######################################################################################################################################################
## Begin DM Reports
######################################################################################################################################################

class DMReports(object):
    def __init__(self):
        self.label = "DM Reports"
        self.description = ""
        self.canRunInBackground = False
        self.category = "Admin Reporting"

    def getParameterInfo(self):
        counties = arcpy.Parameter(
            displayName = "County Layer",
            name = "counties",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        params = [counties]
        return params

    def execute(self, params, messages):
        # layer names of the five element feature classes in the FIND enterprise GDB
        input_features = ["FIND\\Element Point", "FIND\\Element Line", "FIND\\Element Polygon",
        "FIND\\Community or Other Point", "FIND\\Community or Other Polygon", "FIND\\Survey Site"]

        for f in input_features:
            name = os.path.basename(f)
            arcpy.AddMessage(name)
            spatial_join = arcpy.SpatialJoin_analysis(f,counties,os.path.join("memory",name.replace(" ","_")))

            arcpy.AddField_management(spatial_join,"feature_type","TEXT","","",50,"Feature Type")
            with arcpy.da.UpdateCursor(spatial_join,"feature_type") as cursor:
                for row in cursor:
                    row[0] = name
                    cursor.updateRow(row)




