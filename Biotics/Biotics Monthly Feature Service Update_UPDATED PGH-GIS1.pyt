#-------------------------------------------------------------------------------
# Name:        Biotics Feature Servce Monthly Update
# Purpose: This tool can be used to update the Biotics feature service with the monthly exports from Biotics. The tool
# also compares the previous ET with the updated ET and adds records into the ET changes table for all changed ET records.
#
# Author:      MMoore for Pennsylvania Natural Heritage Program
# Created:     2020-04-16
# Updated:
# 2024-05-06 - updated by MMoore
#-------------------------------------------------------------------------------

# Import modules
import os
import arcpy
import arcgis
from arcgis.gis import GIS
from arcgis.features import FeatureLayer
from arcgis.features import FeatureSet
import pandas as pd
import csv
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
            displayName = "WPC GIS Portal Username",
            name = "username",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input")
        password = arcpy.Parameter(
            displayName = "WPC GIS Portal Password",
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

        username = "MollyMoore"
        password = "N1k0C@tM30w!"
        gis = GIS("https://gis.waterlandlife.org/portal", username, password)

        eo_ptreps = r'eo_ptreps'
        eo_reps = r'eo_reps'
        eo_sourcept = r'eo_sourcept'
        eo_sourceln = r'eo_sourceln'
        eo_sourcepy = r'eo_sourcepy'

        fs_ptreps = r"https://gis.waterlandlife.org/server/rest/services/PNHP/Biotics_EDIT/FeatureServer/0"
        fs_reps = r"https://gis.waterlandlife.org/server/rest/services/PNHP/Biotics_EDIT/FeatureServer/1"
        fs_sourcept = r"https://gis.waterlandlife.org/server/rest/services/PNHP/Biotics_EDIT/FeatureServer/2"
        fs_sourceln = r"https://gis.waterlandlife.org/server/rest/services/PNHP/Biotics_EDIT/FeatureServer/3"
        fs_sourcepy = r"https://gis.waterlandlife.org/server/rest/services/PNHP/Biotics_EDIT/FeatureServer/4"
        fs_et = r"https://gis.waterlandlife.org/server/rest/services/PNHP/Biotics_EDIT/FeatureServer/5"
        et_change_server = r"https://gis.waterlandlife.org/server/rest/services/PNHP/Biotics_EDIT/FeatureServer/6"
        visits_server = r"https://gis.waterlandlife.org/server/rest/services/PNHP/Biotics_EDIT/FeatureServer/7"

        ptreps_flayer = FeatureLayer(fs_ptreps)
        reps_flayer = FeatureLayer(fs_reps)
        sourcept_flayer = FeatureLayer(fs_sourcept)
        sourceln_flayer = FeatureLayer(fs_sourceln)
        sourcepy_flayer = FeatureLayer(fs_sourcepy)
        et_flayer = FeatureLayer(fs_et)
        visits_flayer = FeatureLayer(visits_server)

        gdb_ptreps = os.path.join(gdb,eo_ptreps)
        gdb_reps = os.path.join(gdb,eo_reps)
        gdb_sourcept = os.path.join(gdb,eo_sourcept)
        gdb_sourceln = os.path.join(gdb,eo_sourceln)
        gdb_sourcepy = os.path.join(gdb,eo_sourcepy)
        gdb_et = os.path.join(gdb,"ET")
        gdb_visits = os.path.join(gdb,"VISITS")

        et_old = fs_et
        et_new = gdb_et
        et_change = r'W:\\Heritage\\Heritage_Data\\Biotics_datasets.gdb\\ET_changes'

        # get export date - use source lines because it has the fewest records
        with arcpy.da.SearchCursor(gdb_sourceln,"EXPT_DATE") as cursor:
            for row in cursor:
                export_date = row[0]

        # make list of ELSUBIDs in old and new ET tables to get ready for compare
        old_elsubids = sorted({row[0] for row in arcpy.da.SearchCursor(et_old,"ELSUBID")})
        new_elsubids = sorted({row[0] for row in arcpy.da.SearchCursor(et_new,"ELSUBID")})

        insert_fields = ["ELSUBID","change","old_value","new_value","EXPT_DATE"]

        # # get records in new_elsubids that are not in old_elsubids, so classified as added - add to et changes tables
        # arcpy.AddMessage("Checking for ELSUBID additions")
        # added_elsubids = np.setdiff1d(new_elsubids,old_elsubids)
        # for a in added_elsubids:
        #     values = [a,"ELSUBID addition",None,a,export_date]
        #     with arcpy.da.InsertCursor(et_change,insert_fields) as cursor:
        #         cursor.insertRow(values)
        #     with arcpy.da.InsertCursor(et_change_server,insert_fields) as cursor:
        #         cursor.insertRow(values)
        #
        # # records in old_elsubids that are not in new_elsubids, so classified as deleted - add to et changes table
        # arcpy.AddMessage("Checking for ELSUBID deletions")
        # deleted_elsubids = np.setdiff1d(old_elsubids,new_elsubids)
        # for d in deleted_elsubids:
        #     values = [d,"ELSUBID deletion",d,None,export_date]
        #     with arcpy.da.InsertCursor(et_change,insert_fields) as cursor:
        #         cursor.insertRow(values)
        #     with arcpy.da.InsertCursor(et_change_server,insert_fields) as cursor:
        #         cursor.insertRow(values)
        #
        # # get dictionary of fields for comparison with elsubid as key
        # old_et_dict = {int(row[0]):[row[1:]] for row in arcpy.da.SearchCursor(et_old,["ELSUBID","ELCODE","SNAME","SCOMNAME","GRANK","SRANK","EO_Track","USESA","SPROT","PBSSTATUS","SGCN","SENSITV_SP","ER_RULE"])}
        #
        # # define compare fields here
        # change_fields = ["ELCODE","SNAME","SCOMNAME","GRANK","SRANK","EO_Track","USESA","SPROT","PBSSTATUS","SGCN","SENSITV_SP","ER_RULE"]
        # dict_value_index = [0,1,2,3,4,5,6,7,8,9,10,11]
        # # start loop to check for changes between the old ET values and the new ET values
        # for c,i in zip(change_fields,dict_value_index):
        #     arcpy.AddMessage("Checking for changes in " + c)
        #     with arcpy.da.SearchCursor(et_new,["ELSUBID", c]) as cursor:
        #         for row in cursor:
        #             for k,v in old_et_dict.items():
        #                 if k==int(row[0]):
        #                     if row[1] == v[0][i]:
        #                         pass
        #                     elif v[0][i] is None and row[1] == '':
        #                         pass
        #                     elif v[0][i] == '' and row[1] is None:
        #                         pass
        #                     else:
        #                         values = [int(row[0]), c, v[0][i], row[1], export_date]
        #                         with arcpy.da.InsertCursor(et_change,insert_fields) as cursor:
        #                             cursor.insertRow(values)
        #                         with arcpy.da.InsertCursor(et_change_server, insert_fields) as cursor:
        #                             cursor.insertRow(values)
        # # create lists for the feature service layers and the update gdb layers
        # fs_layers = [ptreps_flayer,reps_flayer,sourcept_flayer,sourceln_flayer,sourcepy_flayer,et_flayer,visits_flayer]
        # url_layers = [fs_ptreps,fs_reps,fs_sourcept,fs_sourceln,fs_sourcepy,fs_et,visits_server]
        # gdb_layers = [gdb_ptreps,gdb_reps,gdb_sourcept,gdb_sourceln,gdb_sourcepy,gdb_et,gdb_visits]
        #
        # # loop through feature service layers and delete records
        # for fs, url, g in zip(fs_layers, url_layers, gdb_layers):
        #     arcpy.AddMessage("Deleting features from: " + url)
        #     fs.delete_features(where="objectid > 0")
        #     arcpy.AddMessage("Appending features to: " + url)
        #     arcpy.Append_management(g,url,schema_type="NO_TEST")
        #
        # arcpy.AddMessage("Creating ET Changes .csv Copy for Microsoft Teams")
        # # create ET_changes .csv
        # et_changes_copy = arcpy.ExportTable_conversion(et_change_server,os.path.join("memory","et_changes_copy"))
        # arcpy.JoinField_management(et_changes_copy,"ELSUBID",fs_et,"ELSUBID",["SNAME","SCOMNAME"])
        #
        # # create list of rows that will be written to .csv
        # summary_list = []
        # with arcpy.da.SearchCursor(et_changes_copy, ["ELSUBID","SNAME","SCOMNAME","change","old_value","new_value","EXPT_DATE"]) as cursor:
        #     for row in cursor:
        #         summary_list.append(row)
        #
        # # write to .csv file
        # with open(os.path.join(r"H:\temp", "ET_changes.csv"), 'w', newline='') as csvfile:
        #     csv_output = csv.writer(csvfile)
        #     # write heading rows to .csv
        #     csv_output.writerow(["ELSUBID","SNAME","SCOMNAME","change","old_value","new_value","EXPT_DATE"])
        #     # write dictionary rows to .csv
        #     for row in summary_list:
        #         csv_output.writerow(row)

        # define function to update foreign rel_globalid field with primary globalid based on some other ID value
        def update_rel_guid(parent_feature, primary_key, child_feature, foreign_key, related_guid):
            related_dict = {row[0]: row[1] for row in arcpy.da.SearchCursor(parent_feature, [primary_key, "GlobalID"]) if
                             row[0] is not None}
            with arcpy.da.UpdateCursor(child_feature, [foreign_key, related_guid]) as cursor:
                for row in cursor:
                    for k, v in related_dict.items():
                        if k == row[0]:
                            row[1] = v
                            cursor.updateRow(row)
                        else:
                            pass

        # update relative GlobalIDs in child tables
        update_rel_guid(r"Biotics EDIT\\ET", "ELSUBID", r"Biotics Edit\\ET_changes", "ELSUBID", "ref_GlobalID")
        update_rel_guid(r"Biotics EDIT\\eo_ptreps", "EO_ID", r"Biotics EDIT\\eo_sourcept", "EO_ID","eo_ptreps_GlobalID")
        update_rel_guid(r"Biotics EDIT\\eo_ptreps", "EO_ID", r"Biotics EDIT\\eo_sourceln", "EO_ID","eo_ptreps_GlobalID")
        update_rel_guid(r"Biotics EDIT\\eo_ptreps", "EO_ID", r"Biotics EDIT\\eo_sourcepy", "EO_ID","eo_ptreps_GlobalID")
        update_rel_guid(r"Biotics EDIT\\eo_reps", "EO_ID", r"Biotics EDIT\\eo_sourcept", "EO_ID","eo_reps_GlobalID")
        update_rel_guid(r"Biotics EDIT\\eo_reps", "EO_ID", r"Biotics EDIT\\eo_sourceln", "EO_ID","eo_reps_GlobalID")
        update_rel_guid(r"Biotics EDIT\\eo_reps", "EO_ID", r"Biotics EDIT\\eo_sourcepy", "EO_ID","eo_reps_GlobalID")
        update_rel_guid(r"Biotics EDIT\\eo_sourcept", "SF_ID", r"Biotics EDIT\\VISITS", "SF_ID","eo_sourcept_GlobalID")
        update_rel_guid(r"Biotics EDIT\\eo_sourceln", "SF_ID", r"Biotics EDIT\\VISITS", "SF_ID","eo_sourceln_GlobalID")
        update_rel_guid(r"Biotics EDIT\\eo_sourcepy", "SF_ID", r"Biotics EDIT\\VISITS", "SF_ID","eo_sourcepy_GlobalID")