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
        return

    def execute(self, params, messages):
        # define parameters
        gdb = params[0].valueAsText

        eo_ptreps = r'eo_ptreps'
        eo_reps = r'eo_reps'
        eo_sourcept = r'eo_sourcept'
        eo_sourceln = r'eo_sourceln'
        eo_sourcepy = r'eo_sourcepy'

        arc_prod = arcpy.GetInstallInfo()['ProductName']
        if arc_prod == 'ArcGISPro':
            fs_ptreps = os.path.join(r'BioticsEdit',eo_ptreps)
            fs_reps = os.path.join(r'BioticsEdit',eo_reps)
            fs_sourcept = os.path.join(r'BioticsEdit',eo_sourcept)
            fs_sourceln = os.path.join(r'BioticsEdit',eo_sourceln)
            fs_sourcepy = os.path.join(r'BioticsEdit',eo_sourcepy)
        else:
            fs_ptreps = os.path.join(r'PNHP\BioticsEdit',eo_ptreps)
            fs_reps = os.path.join(r'PNHP\BioticsEdit',eo_reps)
            fs_sourcept = os.path.join(r'PNHP\BioticsEdit',eo_sourcept)
            fs_sourceln = os.path.join(r'PNHP\BioticsEdit',eo_sourceln)
            fs_sourcepy = os.path.join(r'PNHP\BioticsEdit',eo_sourcepy)

        gdb_ptreps = os.path.join(gdb,eo_ptreps)
        gdb_reps = os.path.join(gdb,eo_reps)
        gdb_sourcept = os.path.join(gdb,eo_sourcept)
        gdb_sourceln = os.path.join(gdb,eo_sourceln)
        gdb_sourcepy = os.path.join(gdb,eo_sourcepy)

        fs_layers = [fs_ptreps,fs_reps,fs_sourcept,fs_sourceln,fs_sourcepy]
        gdb_layers = [gdb_ptreps,gdb_reps,gdb_sourcept,gdb_sourceln,gdb_sourcepy]

        for fs,g in zip(fs_layers,gdb_layers):
            with arcpy.da.UpdateCursor(fs,'*') as cursor:
                for row in cursor:
                    cursor.deleteRow()

            arcpy.Append_management(g,fs)



