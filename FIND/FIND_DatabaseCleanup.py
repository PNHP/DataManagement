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
#              6. fills relative GlobalID field with GUID from parent if reference codes match
# Author:      Molly Moore
# Created:     2017-02-13
# Updated:
# 1/26/2023 - updated to fill relative GlobalID field if reference codes match.
#
# To Do List/Future ideas:
#
# -------------------------------------------------------------------------------

# import system modules
import arcpy

# Set tools to overwrite existing outputs
arcpy.env.overwriteOutput = True

workspace = r"C:\Users\mmoore\AppData\Roaming\Esri\ArcGISPro\Favorites\FIND2023_Working_pgh-gis0.sde"
el_pt = r'{}\FIND2023.DBO.el_pt'.format(workspace)
el_line = r'{}\FIND2023.DBO.el_line'.format(workspace)
comm_poly = r'{}\FIND2023.DBO.comm_poly'.format(workspace)
comm_pt = r'{}\FIND2023.DBO.comm_pt'.format(workspace)
el_poly = r'{}\FIND2023.DBO.el_poly'.format(workspace)
survey_poly = r'{}\FIND2023.DBO.survey_poly'.format(workspace)
contacts = r'{}\FIND2023.DBO.contacts'.format(workspace)
species = r'{}\FIND2023.DBO.SpeciesList'.format(workspace)

input_features = [el_pt, el_line, comm_poly, comm_pt, el_poly, survey_poly]
edit = arcpy.da.Editor(workspace)
edit.startEditing(True, True)
edit.startOperation()

# fill back up reference code if null and fill refcode if null
with arcpy.da.UpdateCursor(species, ["refcode", "refcode_backup"]) as cursor:
    for row in cursor:
        # copy refcode to backup refcode field if needed
        if row[0] is not None and row[1] is None:
            row[1] = row[0]
            cursor.updateRow(row)
        # copy backup refcode to refcode if needed
        if row[0] is None and row[1] is not None:
            row[0] = row[1]
            cursor.updateRow(row)

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

# set time to 12:00:00 if not set correctly so weird time change issues don't mess with the date.
for feature in input_features[0:5]:
    with arcpy.da.UpdateCursor(feature, ['date_start', 'date_stop']) as cursor:
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

            if row[1] is None:
                pass
            elif '12:00:00' in str(row[1]):
                pass
            else:
                value = str(row[1])
                update = value.split(' ', 2)[0]
                update = update + ' 12:00:00 PM'
                row[1] = update
                cursor.updateRow(row)

# set time to 12:00:00 if not set correctly so weird time change issues don't mess with the date.
with arcpy.da.UpdateCursor(survey_poly, ['survey_start', 'survey_end']) as cursor:
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

        if row[1] is None:
            pass
        elif '12:00:00' in str(row[1]):
            pass
        else:
            value = str(row[1])
            update = value.split(' ', 2)[0]
            update = update + ' 12:00:00 PM'
            row[1] = update
            cursor.updateRow(row)


# create function to update relative GlobalID based on matching refcodes
def update_rel_guid(parent_feature, primary_key, child_feature, foreign_key, related_guid):
    related_dict = {row[0]: row[1] for row in arcpy.da.SearchCursor(parent_feature, [primary_key, "GlobalID"]) if
                    row[0] is not None}
    with arcpy.da.UpdateCursor(child_feature, [foreign_key, related_guid]) as cursor:
        for row in cursor:
            if row[1] is None:
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
