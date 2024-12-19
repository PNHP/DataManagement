# -------------------------------------------------------------------------------
# Name:        FIND Database Cleanup
# Purpose:     This script is to be run periodically to clean up attributes
#              entered into the FIND database. Currently, the FIND Database
#              Script does the following:
#              1. removes white space from reference codes
#              2. makes all characters in reference codes upper case
#              3. removes default time from 'start_date' and 'end_date' fields
#              4. adds 12:00:00 PM to 'start_date' and 'end_date' fields
#              5. changes any null values in 'dm_stat' field to 'draft'
#              6. fills relative GlobalID field with GUID from parent if reference codes match and rel_GlobalID is null
#              7. loads records from ListMaster Survey123 if they are not duplicates and do not have a null reference code and/or null elem_name
# Author:      Molly Moore
# Created:     2017-02-13
# Updated:
# 1/26/2023 - updated to fill relative GlobalID field if reference codes match.
# 1/12/2024 - updated to include load from ListMaster Survey123 form
#
# To Do List/Future ideas:
#
# -------------------------------------------------------------------------------

# import system modules
import os
import pandas as pd
from arcgis.gis import GIS
import arcpy
import numpy as np

# Set tools to overwrite existing outputs
arcpy.env.overwriteOutput = True

workspace = r"C:\Users\mmoore\AppData\Roaming\Esri\ArcGISPro\Favorites\FIND_Working_pgh-gis1.sde"
el_pt = r'{}\DBO.el_pt'.format(workspace)
el_line = r'{}\DBO.el_line'.format(workspace)
comm_poly = r'{}\DBO.comm_poly'.format(workspace)
comm_pt = r'{}\DBO.comm_pt'.format(workspace)
el_poly = r'{}\DBO.el_poly'.format(workspace)
survey_poly = r'{}\DBO.survey_poly'.format(workspace)
contacts = r'{}\DBO.contacts'.format(workspace)
species = r'{}\DBO.SpeciesList'.format(workspace)

input_features = [el_pt, el_line, comm_poly, comm_pt, el_poly, survey_poly]
edit = arcpy.da.Editor(workspace)
edit.startEditing(False, True)
edit.startOperation()

# fill back up reference code if null and fill refcode if null - DON'T NEED TO DO THIS ANYMORE BECAUSE RELATIONSHIP IS BUILD ON GLOBALID AND REFCODE WON'T GO NULL IF DELETED SURVEY SITE
# with arcpy.da.UpdateCursor(species, ["refcode", "refcode_backup"]) as cursor:
#     for row in cursor:
#         # copy refcode to backup refcode field if needed
#         if row[0] is not None and row[1] is None:
#             row[1] = row[0]
#             cursor.updateRow(row)
#         # copy backup refcode to refcode if needed
#         if row[0] is None and row[1] is not None:
#             row[0] = row[1]
#             cursor.updateRow(row)

# for all element and community FCs and survey site fc, update dm stat to draft where needed and strip white space
# from reference code
for feature in input_features:
    with arcpy.da.UpdateCursor(feature, ['dm_stat', 'refcode']) as cursor:
        for row in cursor:
            # if dm_stat is blank, update to draft status
            if row[0] is None or row[0] == "" or row[0] == " ":
                row[0] = 'dr'
                cursor.updateRow(row)
            if row[1] is None:
                pass
            else:
                # strip white space from reference code and convert to all upper case
                update = str(row[1]).replace(' ', '')
                update = update.upper()
                if row[1] != update:
                    row[1] = update
                    cursor.updateRow(row)

# set time to 12:00:00 if not set correctly so weird time change issues don't mess with the date. THIS IS FOR ELEMENT FEATURES
date_updates = ['date_start', 'date_stop']
for feature in input_features[0:5]:
    for dat in date_updates:
        with arcpy.da.UpdateCursor(feature, dat) as cursor:
            for row in cursor:
                if row[0] is None:
                    pass
                elif '12:00:00' in str(row[0]):
                    pass
                else:
                    value = str(row[0])
                    update = value.split(' ', 2)[0]
                    update = update + ' 12:00:00 PM'
                    row[0] = update
                    cursor.updateRow(row)


# set time to 12:00:00 if not set correctly so weird time change issues don't mess with the date. THIS IS FOR SURVEY SITES
date_updates = ['planned_start_date', 'planned_end_date', 'survey_start', 'survey_end']
for dat in date_updates:
    with arcpy.da.UpdateCursor(survey_poly, dat) as cursor:
        for row in cursor:
            if row[0] is None:
                pass
            elif '12:00:00' in str(row[0]):
                pass
            else:
                value = str(row[0])
                update = value.split(' ', 2)[0]
                update = update + ' 12:00:00 PM'
                row[0] = update
                cursor.updateRow(row)


##################################################################################
## Below is for loading ListMaster records into the FIND Species List
##################################################################################
# define ID number for the ListMaster survey - this can be found @ arcgis.com information page
survey_id = 'aaa4bd7cbd6e4d8daf8fbc35acfcb216'

# define list of fields used in the species list and ListMaster - these should match and be able to be used in retrieving lists from the ListMaster Survey123 form and in inserting them into the FIND Species List
species_fields = ['refcode','plot_id','elem_name','conf','strata','species_cover','specimen_repo','subsite','comm']

# load gis credentials from OS environment variables
wpc_gis_username = os.environ.get("wpc_portal_username")
wpc_gis_password = os.environ.get("wpc_gis_password")
# connect to my arcgis.com account
gis = GIS('https://gis.waterlandlife.org/portal', wpc_gis_username, wpc_gis_password)

# get ListMaster Feature Layer Collection using survey ID number found @ arcgis.com information page
ListMaster = gis.content.get(survey_id)

# define layer and table here - there is only 1 layer and 1 table, so do not need any other comprehension other than to just choose the only one
lm_survey = ListMaster.layers[0]
lm_species = ListMaster.tables[0]

# get all surveys in feature layer and convert to Pandas dataframe
all_surveys = lm_survey.query()
survey_df = all_surveys.sdf

# get all species list entries and convert to Pandas dataframe
all_species = lm_species.query()
species_df = all_species.sdf

# join survey dataframe to species dataframe to get reference code for species list - this is necessary because the relationship is based on globalid and not reference code
merged_df = pd.merge(species_df, survey_df, left_on='parentrowid', right_on='uniquerowid')
merged_df = merged_df.replace({np.nan: None})

# create list of tuples for all records in ListMaster Survey123
ListMaster_records = [tuple(r) for r in merged_df[species_fields].to_numpy()]

# get all species in FIND species list and put them into a list of tuples
current_species = []
with arcpy.da.SearchCursor(species,species_fields) as cursor:
    for row in cursor:
        current_species.append(row)

# for each record in Survey123 ListMaster, check if it already exists in FIND species list - if it does, skip it. if it doesn't, load it in.
for record in ListMaster_records:
    # we also don't want to load records with null reference codes
    if record[0] is None:
        print("A record has a null reference code. It is being skipped")
        pass
    # we also don't want to load records with null element names
    elif record[2] is None:
        print("A record has a null element name. It is being skipped.")
        pass
    elif record in current_species:
        print("A record of "+record[2]+" from survey with reference code " + record[0] + " is already in the FIND species list.")
        pass
    else:
        with arcpy.da.InsertCursor(species,species_fields) as cursor:
            cursor.insertRow(record)

# Delete identical records in the FIND species list - this is a general management step
arcpy.management.DeleteIdentical(species, species_fields)


################################################################################
### below is for updating relative GlobalID in foreign tables if matching refcodes
################################################################################


# create function to update related GlobalID based on matching refcodes
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
update_rel_guid(survey_poly, "refcode", el_pt, "refcode", "rel_GlobalID")
update_rel_guid(survey_poly, "refcode", el_line, "refcode", "rel_GlobalID")
update_rel_guid(survey_poly, "refcode", el_poly, "refcode", "rel_GlobalID")
update_rel_guid(survey_poly, "refcode", comm_pt, "refcode", "rel_GlobalID")
update_rel_guid(survey_poly, "refcode", comm_poly, "refcode", "rel_GlobalID")
update_rel_guid(survey_poly, "refcode", species, "refcode", "rel_GlobalID")
update_rel_guid(survey_poly, "refcode", contacts, "refcode", "surv_rel_GlobalID")


edit.stopOperation()
edit.stopEditing(True)
