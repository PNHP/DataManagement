"""
# Name: Biotics Feature Service Monthly Update - Version 2
# Purpose: This script should be used to update the Biotics feature services from the local exported .gdb layers.
#
# Author: MMoore for Pennsylvania Natural Heritage Program
# Created: 2024-11-21
"""

# Import modules
import os
import datetime
import numpy as np
import arcpy
from arcgis.features import FeatureLayer

# # load gis credentials from OS environment variables - these need to be setup in your operating system environment variables
wpc_gis_username = os.environ.get("wpc_portal_username")
wpc_gis_password = os.environ.get("wpc_gis_password")
# connect to Portal account
gis = GIS('https://gis.waterlandlife.org/portal', wpc_gis_username, wpc_gis_password)

# Set tools to overwrite existing outputs
arcpy.env.overwriteOutput = True
arcpy.env.workspace = "memory"

######################################################################################################################################################
## define feature service URLs and .gdb file paths
######################################################################################################################################################
# define .gdb file paths
biotics_file_gdb = r"W:/Heritage/Heritage_Data/Biotics_datasets.gdb"
eo_ptreps_gdb = os.path.join(biotics_file_gdb, "eo_ptreps")
eo_reps_gdb = os.path.join(biotics_file_gdb, "eo_reps")
eo_sourcept_gdb = os.path.join(biotics_file_gdb, "eo_sourcept")
eo_sourceln_gdb = os.path.join(biotics_file_gdb, "eo_sourceln")
eo_sourcepy_gdb = os.path.join(biotics_file_gdb, "eo_sourcepy")
et_gdb = os.path.join(biotics_file_gdb, "ET")
visits_gdb = os.path.join(biotics_file_gdb, "VISITS")
et_change_gdb = os.path.join(biotics_file_gdb, "ET_changes")

# define feature service URLs
eo_ptreps_url = r"https://gis.waterlandlife.org/server/rest/services/PNHP/Biotics_EDIT/FeatureServer/0"
eo_reps_url = r"https://gis.waterlandlife.org/server/rest/services/PNHP/Biotics_EDIT/FeatureServer/1"
eo_sourcept_url = r"https://gis.waterlandlife.org/server/rest/services/PNHP/Biotics_EDIT/FeatureServer/2"
eo_sourceln_url = r"https://gis.waterlandlife.org/server/rest/services/PNHP/Biotics_EDIT/FeatureServer/3"
eo_sourcepy_url = r"https://gis.waterlandlife.org/server/rest/services/PNHP/Biotics_EDIT/FeatureServer/4"
et_url = r"https://gis.waterlandlife.org/server/rest/services/PNHP/Biotics_EDIT/FeatureServer/5"
visits_url = r"https://gis.waterlandlife.org/server/rest/services/PNHP/Biotics_EDIT/FeatureServer/7"
et_change_url = r"https://gis.waterlandlife.org/server/rest/services/PNHP/Biotics_EDIT/FeatureServer/6"

########################################################################################################################
# First we will compare this month ET to last month ET to check for changes and insert changes into the ET Changes Table
########################################################################################################################
# we are just going to redefine these so that it's not as confusing
et_old = et_url
et_new = et_gdb

# let's get the current export date - we'll use the source line dataset because it does not have that many features, so will be fastest - there is probably a better way to do this?
with arcpy.da.SearchCursor(eo_sourceln_gdb, "EXPT_DATE") as cursor:
    for row in cursor:
        export_date = row[0]
# get lists of ELSUBIDs in both the old ET and the new ET
old_elsubids = sorted({row[0] for row in arcpy.da.SearchCursor(et_old, "ELSUBID")})
new_elsubids = sorted({row[0] for row in arcpy.da.SearchCursor(et_new, "ELSUBID")})

# define list of fields for the insert cursor for the ET changes table
insert_fields = ["ELSUBID", "change", "old_value", "new_value", "EXPT_DATE"]

# get records in new_elsubids that are not in old_elsubids - these will be classified as added - add to et changes tables
arcpy.AddMessage("Checking for ELSUBID additions")
# get ELSUBIDs in new ET that were NOT in the old ET
added_elsubids = np.setdiff1d(new_elsubids, old_elsubids)
# for each, insert record into ET changes tables - we are currently maintaining the ET changes table on the W: .gdb version and the feature service
for a in added_elsubids:
    values = [a, "ELSUBID addition", None, a, export_date]
    with arcpy.da.InsertCursor(et_change_gdb, insert_fields) as cursor:
        cursor.insertRow(values)
    with arcpy.da.InsertCursor(et_change_url, insert_fields) as cursor:
        cursor.insertRow(values)

# records in old_elsubids that are not in new_elsubids - these are classified as deleted - add to et changes table
arcpy.AddMessage("Checking for ELSUBID deletions")
# get ELSUBIDs in old ET that are NOT in the new ET
deleted_elsubids = np.setdiff1d(old_elsubids, new_elsubids)
# for each, insert record into ET changes tables - we are currently maintaining the ET changes table on the W: .gdb version and the feature service
for d in deleted_elsubids:
    values = [d, "ELSUBID deletion", d, None, export_date]
    with arcpy.da.InsertCursor(et_change_gdb, insert_fields) as cursor:
        cursor.insertRow(values)
    with arcpy.da.InsertCursor(et_change_url, insert_fields) as cursor:
        cursor.insertRow(values)

# get dictionary of fields for comparison with elsubid as key
old_et_dict = {int(row[0]): [row[1:]] for row in arcpy.da.SearchCursor(et_old,
                                                                       ["ELSUBID", "ELCODE", "SNAME", "SCOMNAME",
                                                                        "GRANK", "SRANK", "EO_Track", "USESA", "SPROT",
                                                                        "PBSSTATUS", "SGCN", "SENSITV_SP", "ER_RULE"])}

# define compare fields here and create a list of dictionary value indices
change_fields = ["ELCODE", "SNAME", "SCOMNAME", "GRANK", "SRANK", "EO_Track", "USESA", "SPROT", "PBSSTATUS", "SGCN",
                 "SENSITV_SP", "ER_RULE"]
dict_value_index = list(range(len(change_fields)))
# start loop to check for changes between the old ET values and the new ET values
for c, i in zip(change_fields, dict_value_index):
    arcpy.AddMessage("Checking for changes in " + c)
    with arcpy.da.SearchCursor(et_new, ["ELSUBID", c]) as cursor:
        for row in cursor:
            for k, v in old_et_dict.items():
                if k == int(row[0]):
                    if row[1] == v[0][i]:
                        pass
                    elif v[0][i] is None and row[1] == '':
                        pass
                    elif v[0][i] == '' and row[1] is None:
                        pass
                    else:
                        values = [int(row[0]), c, v[0][i], row[1], export_date]
                        with arcpy.da.InsertCursor(et_change_gdb, insert_fields) as cursor:
                            cursor.insertRow(values)
                        with arcpy.da.InsertCursor(et_change_url, insert_fields) as cursor:
                            cursor.insertRow(values)

biotics_sde = r"C:\\Users\\mmoore\\AppData\\Roaming\\Esri\\ArcGISPro\\Favorites\\PNHP_Working_pgh-gis1.sde"
visits_target = os.path.join(biotics_sde, "DBO.VISITS")
eo_ptreps_target = os.path.join(biotics_sde, "DBO.Biotics", "DBO.eo_ptreps")
eo_reps_target = os.path.join(biotics_sde, "DBO.Biotics", "DBO.eo_reps")
eo_sourcept_target = os.path.join(biotics_sde, "DBO.Biotics", "DBO.eo_sourcept")
eo_sourceln_target = os.path.join(biotics_sde, "DBO.Biotics", "DBO.eo_sourceln")
eo_sourcepy_target = os.path.join(biotics_sde, "DBO.Biotics", "DBO.eo_sourcepy")
et_target = os.path.join(biotics_sde, "DBO.ET")
et_change_target = os.path.join(biotics_sde, "DBO.ET_changes")

# create lists for the feature service layers and the update gdb layers
fs_layers = [visits_url, eo_ptreps_url, eo_reps_url, eo_sourcept_url, eo_sourceln_url, eo_sourcepy_url, et_url]
gdb_layers = [visits_gdb, eo_ptreps_gdb, eo_reps_gdb, eo_sourcept_gdb, eo_sourceln_gdb, eo_sourcepy_gdb, et_gdb]
target_layers = [visits_target, eo_ptreps_target, eo_reps_target, eo_sourcept_target, eo_sourceln_target,
                 eo_sourcepy_target, et_target]

for fs, g, target in zip(fs_layers, gdb_layers, target_layers):
    # create feature layer object
    feature_layer = FeatureLayer(fs)
    # delete all features in feature layer - can we figure out how to use truncate here?
    print("Deleting features from: " + fs)
    feature_layer.delete_features(where="objectid > 0")
    print("Appending features to: " + fs)
    arcpy.Append_management(g, target, schema_type="NO_TEST")


# define function to update foreign rel_globalid field with primary globalid based on some other ID value
def update_rel_guid(parent_feature, primary_key, child_feature, foreign_key, related_guid):
    related_dict = {row[0]: row[1] for row in arcpy.da.SearchCursor(parent_feature, [primary_key, "GlobalID"]) if
                    row[0] is not None}
    edit = arcpy.da.Editor(biotics_sde)
    edit.startEditing(False, True)
    edit.startOperation()
    with arcpy.da.UpdateCursor(child_feature, [foreign_key, related_guid]) as cursor:
        for row in cursor:
            for k, v in related_dict.items():
                if k == row[0]:
                    row[1] = v
                    cursor.updateRow(row)
                else:
                    pass
    edit.stopOperation()
    edit.stopEditing(True)


# update relative GlobalIDs in child tables
update_rel_guid(et_target, "ELSUBID", et_change_target, "ELSUBID", "ref_GlobalID")
update_rel_guid(eo_ptreps_target, "EO_ID", eo_sourcept_target, "EO_ID", "eo_ptreps_GlobalID")
update_rel_guid(eo_ptreps_target, "EO_ID", eo_sourceln_target, "EO_ID", "eo_ptreps_GlobalID")
update_rel_guid(eo_ptreps_target, "EO_ID", eo_sourcepy_target, "EO_ID", "eo_ptreps_GlobalID")
update_rel_guid(eo_reps_target, "EO_ID", eo_sourcept_target, "EO_ID", "eo_reps_GlobalID")
update_rel_guid(eo_reps_target, "EO_ID", eo_sourceln_target, "EO_ID", "eo_reps_GlobalID")
update_rel_guid(eo_reps_target, "EO_ID", eo_sourcepy_target, "EO_ID", "eo_reps_GlobalID")
update_rel_guid(eo_sourcept_target, "SF_ID", visits_target, "SF_ID", "eo_sourcept_GlobalID")
update_rel_guid(eo_sourceln_target, "SF_ID", visits_target, "SF_ID", "eo_sourceln_GlobalID")
update_rel_guid(eo_sourcepy_target, "SF_ID", visits_target, "SF_ID", "eo_sourcepy_GlobalID")

# ADD SOMETHING TO FILL THE NHA/CPP QUALIFY FIELDS!!!!
# calculate 50 years ago to use with state listed plants
year = datetime.datetime.now().year - 50
where_clause = "(((ELCODE LIKE 'AB%' AND LASTOBS >= '1990') OR (ELCODE = 'ABNKC12060' AND LASTOBS >= '1980')) OR (((ELCODE LIKE 'P%' OR ELCODE LIKE 'N%' OR ELCODE LIKE 'C%' OR ELCODE LIKE 'H%' OR ELCODE LIKE 'G%') AND (LASTOBS >= '{0}')) OR ((ELCODE LIKE 'P%' OR ELCODE LIKE 'N%') AND (USESA = 'LE' OR USESA = 'LT') AND (LASTOBS >= '1950'))) OR (((ELCODE LIKE 'AF%' OR ELCODE LIKE 'AA%' OR ELCODE LIKE 'AR%') AND (LASTOBS >= '1950')) OR (ELCODE = 'ARADE03011')) OR (((ELCODE LIKE 'AM%' OR ELCODE LIKE 'OBAT%') AND ELCODE <> 'AMACC01150' AND LASTOBS >= '1970') OR (ELCODE = 'AMACC01100' AND LASTOBS >= '1950') OR (ELCODE = 'AMACC01150' AND LASTOBS >= '1985')) OR (((ELCODE LIKE 'IC%' OR ELCODE LIKE 'IIEPH%' OR ELCODE LIKE 'IITRI%' OR ELCODE LIKE 'IMBIV%' OR ELCODE LIKE 'IMGAS%' OR ELCODE LIKE 'IP%' OR ELCODE LIKE 'IZ%') AND LASTOBS >= '1950') OR (ELCODE LIKE 'I%' AND ELCODE NOT LIKE 'IC%' AND ELCODE NOT LIKE 'IIEPH%' AND ELCODE NOT LIKE 'IITRI%' AND ELCODE NOT LIKE 'IMBIV%' AND ELCODE NOT LIKE 'IMGAS%' AND ELCODE NOT LIKE 'IP%' AND ELCODE NOT LIKE 'IZ%' AND LASTOBS >= '1980'))OR (LASTOBS = '' OR LASTOBS = ' ')) AND (EO_TRACK = 'Y' OR EO_TRACK = 'W') AND (LASTOBS <> 'NO DATE' AND EORANK <> 'X' AND EORANK <> 'X?') AND (EST_RA <> 'Very Low' OR EST_RA <> 'Low')".format(
    year)
edit = arcpy.da.Editor(biotics_sde)
edit.startEditing(False, True)
edit.startOperation()
with arcpy.da.UpdateCursor(eo_reps_target, ["CPPEligible", "NHAEligible"], where_clause) as cursor:
    for row in cursor:
        row[0] = "Y"
        row[1] = "Y"
        cursor.updateRow(row)
edit.stopOperation()
edit.stopEditing(True)

edit = arcpy.da.Editor(biotics_sde)
edit.startEditing(False, True)
edit.startOperation()
with arcpy.da.UpdateCursor(eo_reps_target, ["CPPEligible", "NHAEligible"]) as cursor:
    for row in cursor:
        if row[0] is None:
            row[0] = "N"
        if row[1] is None:
            row[1] = "N"
        cursor.updateRow(row)
edit.stopOperation()
edit.stopEditing(True)


# # We are going to start the section where we replace the features with the new features
# # load gis credentials from OS environment variables - these need to be setup in your operating system environment variables
# wpc_gis_username = os.environ.get("wpc_portal_username")
# wpc_gis_password = os.environ.get("wpc_gis_password")
# # connect to Portal account
# gis = GIS('https://gis.waterlandlife.org/portal', wpc_gis_username, wpc_gis_password)
#
# d = arcpy.Describe(g)
# if d.datatype == "Table":
#     # Convert feature class to NumPy array
#     fields = [f.name for f in arcpy.ListFields(g)]
#     array = arcpy.da.FeatureClassToNumPyArray(g, fields)
#     # Create DataFrame from NumPy array
#     df = pd.DataFrame(array)
# elif d.datatype == "FeatureClass":
#     df = GeoAccessor.from_featureclass(g)
# else:
#     print("The data type is not recognized. Something horrible has gone wrong!")
#
# if g == visits_gdb:
#     df['VISIT_NOTES'] = df['VISIT_NOTES'].replace('[<>]', '', regex=True)
#
# df = df.fillna(np.nan)
# df = df.replace({np.nan: None})
# df['EO_ID'] = df['EO_ID'].fillna(0)
#
# feature_set = df.spatial.to_featureset()
# feature_layer.edit_features(adds=feature_set)


