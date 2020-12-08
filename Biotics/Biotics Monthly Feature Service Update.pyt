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
        username = arcpy.Parameter(
            displayName = "WPC GIS Username",
            name = "username",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input")
        password = arcpy.Parameter(
            displayName = "WPC GIS Password",
            name = "password",
            datatype = "GPEncryptedString",
            parameterType = "Required",
            direction = "Input")
        params = [gdb, username, password]
        return params

    def execute(self, params, messages):
        # define parameters
        gdb = params[0].valueAsText
        username = params[1].valueAsText
        password = params[2].valueAsText

        system_username = getuser().upper()

        working_db = arcpy.CreateDatabaseConnection_management("H:","PNHP.sde","SQL_SERVER","pgh-gis0","OPERATING_SYSTEM_AUTH",username,password,"SAVE_USERNAME","PNHP","#","TRANSACTIONAL","DBO.Working")
        arcpy.CreateVersion_management(working_db,"DBO.Working",username+"_TEMP","PUBLIC")
        pnhp_db = arcpy.CreateDatabaseConnection_management("H:","PNHP_"+username+".sde","SQL_SERVER","pgh-gis0","OPERATING_SYSTEM_AUTH",username,password,"SAVE_USERNAME","PNHP","#","TRANSACTIONAL",'"WPC\\'+system_username+'".'+username+"_TEMP")

        biotics_db_path = r"PNHP.DBO.Biotics\\PNHP.DBO."

        eo_ptreps = r'eo_ptreps'
        eo_reps = r'eo_reps'
        eo_sourcept = r'eo_sourcept'
        eo_sourceln = r'eo_sourceln'
        eo_sourcepy = r'eo_sourcepy'

        fs_ptreps = os.path.join(str(pnhp_db),biotics_db_path+eo_ptreps)
        fs_reps = os.path.join(str(pnhp_db),biotics_db_path+eo_reps)
        fs_sourcept = os.path.join(str(pnhp_db),biotics_db_path+eo_sourcept)
        fs_sourceln = os.path.join(str(pnhp_db),biotics_db_path+eo_sourceln)
        fs_sourcepy = os.path.join(str(pnhp_db),biotics_db_path+eo_sourcepy)
        fs_et = os.path.join(str(pnhp_db),"PNHP.DBO.ET")

        gdb_ptreps = os.path.join(gdb,eo_ptreps)
        gdb_reps = os.path.join(gdb,eo_reps)
        gdb_sourcept = os.path.join(gdb,eo_sourcept)
        gdb_sourceln = os.path.join(gdb,eo_sourceln)
        gdb_sourcepy = os.path.join(gdb,eo_sourcepy)
        gdb_et = os.path.join(gdb,"ET")

        fs_layers = [fs_ptreps,fs_reps,fs_sourcept,fs_sourceln,fs_sourcepy,fs_et]
        gdb_layers = [gdb_ptreps,gdb_reps,gdb_sourcept,gdb_sourceln,gdb_sourcepy,gdb_et]

        edit = arcpy.da.Editor(pnhp_db)
        edit.startEditing(False,True)
        edit.startOperation()

        for fs,g in zip(fs_layers,gdb_layers):
            arcpy.AddMessage("Deleting features from: "+fs)
            with arcpy.da.UpdateCursor(fs,'*') as cursor:
                for row in cursor:
                    cursor.deleteRow()

        for fs,g in zip(fs_layers,gdb_layers):
            arcpy.AddMessage("Appending features to: "+fs)
            arcpy.Append_management(g,fs,schema_type="NO_TEST")

        edit.stopOperation()
        edit.stopEditing(True)

        arcpy.ReconcileVersions_management(pnhp_db,"ALL_VERSIONS","DBO.Working",'"WPC\\'+system_username+'".'+username+"_TEMP","LOCK_ACQUIRED","#","#","FAVOR_EDIT_VERSION","POST","DELETE_VERSION","#","#","DO_NOT_RECONCILE")

        arcpy.Delete_management(pnhp_db)
        del(pnhp_db)
        arcpy.DeleteVersion_management(working_db,'"WPC\\'+system_username+'".'+username+"_TEMP")
        arcpy.Delete_management(working_db)
        working_db = arcpy.CreateDatabaseConnection_management("H:","PNHP.sde","SQL_SERVER","pgh-gis0","OPERATING_SYSTEM_AUTH",username,password,"SAVE_USERNAME","PNHP","#","TRANSACTIONAL","DBO.Working")