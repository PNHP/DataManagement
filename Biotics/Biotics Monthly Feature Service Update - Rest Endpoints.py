#-------------------------------------------------------------------------------
# Name:        Biotics Feature Servce Monthly Update
# Purpose:
#
# Author:      MMoore
#
# Created:     04/16/2020
# Copyright:   (c) MMoore 2020
# Licence:     <your licence>
#-------------------------------------------------------------------------------

# Import modules
import arcpy, time, datetime, sys, os
from getpass import getuser

# Set tools to overwrite existing outputs
arcpy.env.overwriteOutput = True
arcpy.env.workspace = "memory"

######################################################################################################################################################
##
######################################################################################################################################################

class Toolbox(object):
    def __init__(self):
        self.label = "Biotics Monthly Feature Service Monthly Update"
        self.alias = "Biotics Monthly Feature Service Monthly Update"
        self.tools = [BioticsUpdate]

######################################################################################################################################################
##
######################################################################################################################################################

class BioticsUpdate(object):
    def __init__(self):
        self.label = "Biotics Feature Service Update"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        gdb = arcpy.Parameter(
            displayName = "Local Biotics File Geodatabase to Upload to Feature Service",
            name = "gdb",
            datatype = "DEWorkspace",
            parameterType = "Required",
            direction = "Input")

    def execute(self, params, messages):
        # define parameters
        gdb = params[0].valueAsText

        #establish rest endpoint urls
        eo_ptreps = r'https://maps.waterlandlife.org/arcgis/rest/services/PNHP/BioticsEdit/FeatureServer/0'
        eo_reps = r'https://maps.waterlandlife.org/arcgis/rest/services/PNHP/BioticsEdit/FeatureServer/1'
        eo_sourcept = r'https://maps.waterlandlife.org/arcgis/rest/services/PNHP/BioticsEdit/FeatureServer/2'
        eo_sourceln = r'https://maps.waterlandlife.org/arcgis/rest/services/PNHP/BioticsEdit/FeatureServer/3'
        eo_sourcepy = r'https://maps.waterlandlife.org/arcgis/rest/services/PNHP/BioticsEdit/FeatureServer/4'
        et = r'https://maps.waterlandlife.org/arcgis/rest/services/PNHP/BioticsEdit/FeatureServer/5'

        eo_ptreps_gdb = os.path.join(gdb,"eo_ptreps")
        eo_reps_gdb = os.path.join(gdb,"eo_reps")
        eo_sourcept_gdb = os.path.join(gdb,"eo_sourcept")
        eo_sourceln_gdb = os.path.join(gdb,"eo_sourceln")
        eo_sourcepy_gdb = os.path.join(gdb,"eo_sourcepy")
        et_gdb = os.path.join(gdb,"ET")

        feature_service_layers = [eo_ptreps,eo_reps,eo_sourcept,eo_sourceln,eo_sourcepy]
        gdb_layers = [eo_ptreps_gdb,eo_reps_gdb,eo_sourcept_gdb,eo_sourceln_gdb,eo_sourcepy_gdb]

        for f,g in zip(feature_service_layers,gdb_layers):
            fs = arcpy.FeatureSet()
            fs_load = fs.load(f)
            arcpy.AddMessage("Deleting features from "+f+" at "+ datetime.now().strftime("%H:%M:%S"))
            with arcpy.da.updateCursor(fs_load,"*") as cursor:
                for row in cursor:
                    cursor.deleteRow()
            arcpy.AddMessage("Appending features to "+f+" at "+datetime.now().strftime("%H:%M:%S"))
            arcpy.Append_management(g,f,"NO_TEST")




