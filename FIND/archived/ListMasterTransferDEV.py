# import packages
import os
import pandas as pd
from arcgis.gis import GIS
import arcpy
import numpy as np

# need to create some kind of password encryption here so my info isn't just in the script
gis_username = os.getenv('wpc_gis_username')
gis_password = os.getenv('wpc_gis_password')

# define ID number for the ListMaster survey - this can be found @ arcgis.com information page
survey_id = 'efac50dc6b95479e9329092ae4c454c1'

# define path to species list in FIND
workspace = r"C:\Users\mmoore\AppData\Roaming\Esri\ArcGISPro\Favorites\FIND_Working_pgh-gis0.sde"
species = r'{}\FIND2024.DBO.SpeciesList'.format(workspace)
#species = r"H:\\temp\\FIND_testing.gdb\\sp_list"

edit = arcpy.da.Editor(workspace)
edit.startEditing(True, True)
edit.startOperation()

# define list of fields used in the species list and ListMaster - these should match and be able to be used in retrieving lists from the ListMaster Survey123 form and in inserting them into the FIND Species List
species_fields = ['refcode','plot_id','elem_name','conf','strata','species_cover','specimen_repo','subsite','comm']

# connect to my arcgis.com account
gis = GIS('https://www.arcgis.com', "mmooreWPC", "N1k0C@tM30w!")

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
merged_df = pd.merge(species_df, survey_df, left_on='parentglobalid', right_on='globalid')
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
    if record in current_species:
        print("A record of "+record[2]+" from survey with reference code " + record[0] + " is already in the FIND species list.")
        pass
    # we also don't want to load records with null reference codes
    elif record[0] is None:
        print("A record has a null reference code. It is being skipped")
        pass
    # we also don't want to load records with null element names
    elif record[2] is None:
        print("A record has a null element name. It is being skipped.")
        pass
    else:
        with arcpy.da.InsertCursor(species,species_fields) as cursor:
            cursor.insertRow(record)

# Delete identical records in the FIND species list - this is a general management step
arcpy.management.DeleteIdentical(species, species_fields)

edit.stopOperation()
edit.stopEditing(True)