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
import numpy as np

# Set tools to overwrite existing outputs
arcpy.env.overwriteOutput = True
arcpy.env.workspace = "memory"

######################################################################################################################################################
## define toolbox class
######################################################################################################################################################

class Toolbox(object):
    def __init__(self):
        self.label = "Biotics Monthly Feature Service Monthly Update"
        self.alias = "Biotics Monthly Feature Service Monthly Update"
        self.tools = [BioticsUpdate]

######################################################################################################################################################
## Biotics Feature Service Update tool
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

        pnhp_db = r"C:\\Users\\MMoore\\AppData\\Roaming\\Esri\\ArcGISPro\\Favorites\\PNHP_Working_pgh-gis0.sde"
##        arcpy.CreateVersion_management(working_db,"DBO.Working",username+"_TEMP","PUBLIC")
##        pnhp_db = arcpy.CreateDatabaseConnection_management("H:","PNHP_"+username+".sde","SQL_SERVER","pgh-gis0","OPERATING_SYSTEM_AUTH",username,password,"SAVE_USERNAME","PNHP","#","TRANSACTIONAL",'"WPC\\'+system_username+'".'+username+"_TEMP")

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
        et_change_server = os.path.join(str(pnhp_db), r"PNHP.DBO.ET_changes")

        gdb_ptreps = os.path.join(gdb,eo_ptreps)
        gdb_reps = os.path.join(gdb,eo_reps)
        gdb_sourcept = os.path.join(gdb,eo_sourcept)
        gdb_sourceln = os.path.join(gdb,eo_sourceln)
        gdb_sourcepy = os.path.join(gdb,eo_sourcepy)
        gdb_et = os.path.join(gdb,"ET")

        et_old = fs_et
        et_new = gdb_et
        et_change = r'W:\\Heritage\\Heritage_Data\\Biotics_datasets.gdb\\ET_changes'


        with arcpy.da.SearchCursor(gdb_sourceln,"EXPT_DATE") as cursor:
            for row in cursor:
                export_date = row[0]
        old_elsubids = sorted({row[0] for row in arcpy.da.SearchCursor(et_old,"ELSUBID")})
        new_elsubids = sorted({row[0] for row in arcpy.da.SearchCursor(et_new,"ELSUBID")})

        insert_fields = ["ELSUBID","change","old_value","new_value","EXPT_DATE"]

        #records in new_elsubids that are not in old_elsubids, so therefore classified as added
        arcpy.AddMessage("Checking for ELSUBID additions")
        added_elsubids = np.setdiff1d(new_elsubids,old_elsubids)
        for a in added_elsubids:
            values = [a,"ELSUBID addition",None,a,export_date]
            with arcpy.da.InsertCursor(et_change,insert_fields) as cursor:
                cursor.insertRow(values)
            with arcpy.da.InsertCursor(et_change_server,insert_fields) as cursor:
                cursor.insertRow(values)

        #records in old_elsubids that are not in new_elsubids, so therefore classified as deleted
        arcpy.AddMessage("Checking for ELSUBID deletions")
        deleted_elsubids = np.setdiff1d(old_elsubids,new_elsubids)
        for d in deleted_elsubids:
            values = [d,"ELSUBID deletion",d,None,export_date]
            with arcpy.da.InsertCursor(et_change,insert_fields) as cursor:
                cursor.insertRow(values)
            with arcpy.da.InsertCursor(et_change_server,insert_fields) as cursor:
                cursor.insertRow(values)

        old_et_dict = {int(row[0]):[row[1:]] for row in arcpy.da.SearchCursor(et_old,["ELSUBID","ELCODE","SNAME","SCOMNAME","GRANK","SRANK","EO_Track","USESA","SPROT","PBSSTATUS","SGCN","SENSITV_SP","ER_RULE"])}

        change_fields = ["ELCODE","SNAME","SCOMNAME","GRANK","SRANK","EO_Track","USESA","SPROT","PBSSTATUS","SGCN","SENSITV_SP","ER_RULE"]
        dict_value_index = [0,1,2,3,4,5,6,7,8,9,10,11]
        for c,i in zip(change_fields,dict_value_index):
            arcpy.AddMessage("Checking for changes in " + c)
            with arcpy.da.SearchCursor(et_new,["ELSUBID", c]) as cursor:
                for row in cursor:
                    for k,v in old_et_dict.items():
                        if k==int(row[0]):
                            if row[1] == v[0][i]:
                                pass
                            else:
                                values = [int(row[0]), c, v[0][i], row[1], export_date]
                                with arcpy.da.InsertCursor(et_change,insert_fields) as cursor:
                                    cursor.insertRow(values)
                                with arcpy.da.InsertCursor(et_change_server, insert_fields) as cursor:
                                    cursor.insertRow(values)

        fs_layers = [fs_ptreps,fs_reps,fs_sourcept,fs_sourceln,fs_sourcepy,fs_et]
        gdb_layers = [gdb_ptreps,gdb_reps,gdb_sourcept,gdb_sourceln,gdb_sourcepy,gdb_et]

        edit = arcpy.da.Editor(pnhp_db)
        edit.startEditing(False,False)
        edit.startOperation()

        for fs,g in zip(fs_layers,gdb_layers):
            arcpy.AddMessage("Deleting features from: "+fs)
            with arcpy.da.UpdateCursor(fs,'OBJECTID') as cursor:
                for row in cursor:
                    if row[0] is not None:
                        cursor.deleteRow()

        for fs,g in zip(fs_layers,gdb_layers):
            arcpy.AddMessage("Appending features to: "+fs)
            arcpy.Append_management(g,fs,schema_type="NO_TEST")

        edit.stopOperation()
        edit.stopEditing(True)

##        arcpy.ReconcileVersions_management(pnhp_db,"ALL_VERSIONS","DBO.Working",'"WPC\\'+system_username+'".'+"mmoore_TEMP","LOCK_ACQUIRED","#","#","FAVOR_EDIT_VERSION","POST","DELETE_VERSION","#","#","DO_NOT_RECONCILE")
        arcpy.Delete_management(pnhp_db)
        del(pnhp_db)