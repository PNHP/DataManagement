#-------------------------------------------------------------------------------
# Name:        FIND Reports
# Purpose:
# Author:      MMoore
# Created:     07/06/2023
#-------------------------------------------------------------------------------

# Import modules
# import system modules
import arcpy, os, datetime
from arcpy import env
from arcpy.sa import *
import csv

# Set tools to overwrite existing outputs
arcpy.env.overwriteOutput = True
arcpy.env.workspace = "memory"

######################################################################################################################################################
## define toolbox class
######################################################################################################################################################

class Toolbox(object):
    def __init__(self):
        self.label = "FIND Reports Toolbox"
        self.alias = "FIND Reports Toolbox"
        self.tools = [FINDStatusReports]

######################################################################################################################################################
## Begin FIND Monthly Reports Tool
######################################################################################################################################################

class FINDStatusReports(object):
    def __init__(self):
        self.label = "FIND Status Reports"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        return True

    def execute(self, parameters, messages):

        # input features from feature service
        input_features = [r"FIND\\Element Point", r"FIND\\Element Line", r"FIND\\Element Polygon", r"FIND\\Community or Other Point", r"FIND\\Community or Other Polygon"]

        # file names that are used for temporary output element feature classes
        elementShapefiles = ["element_point", "element_line", "community_poly", "community_point", "element_poly", "survey_site"]

        # file names that are used for temporary element tables
        elementTables = ["element_point1", "element_line1", "community_poly1", "community_point1", "element_poly1", "survey_site1"]

        # path to county layer
        counties = r"County"

        # path to Biotics ET
        et = r"ET"

        # path to folder where DM reports will be saved as Excel files
        ReportsPath = r"P:\Conservation Programs\Natural Heritage Program\Data Management\Instructions, procedures and documentation\FIND\Reports"

        for i, shape_output, table_output in zip(input_features, elementShapefiles, elementTables):
            target_features = i
            print(target_features)
            element_features = os.path.join(r"H:\\temp\\temp.gdb", shape_output)

            # # create fieldmap
            # fieldmappings = arcpy.FieldMappings()
            # fieldmappings.addTable(target_features)
            # fieldmappings.addTable(counties)
            #
            # # fields to be kept after spatial join
            # keepFields = ["COUNTY_NAM", "refcode", "created_user", "created_date", "dm_stat", "dm_stat_comm", "last_up_by",
            # "last_up_on", "element_type", "elem_name", "id_prob", "id_prob_comm", "specimen_taken", "specimen_count",
            # "specimen_desc", "curatorial_meth", "specimen_repo", "voucher_photo", "elem_found", "archive", "X", "Y"]
            #
            # # remove all fields not in keep fields from field map
            # for field in fieldmappings.fields:
            #    if field.name not in keepFields:
            #        fieldmappings.removeFieldMap(fieldmappings.findFieldMapIndex(field.name))

            # run the spatial join tool
            # spatial_join = arcpy.SpatialJoin_analysis(target_features, counties, element_features, field_mapping=fieldmappings)

            # run the spatial join tool
            spatial_join = arcpy.SpatialJoin_analysis(target_features, counties, element_features)

            arcpy.AddField_management(spatial_join,"element_type","TEXT",field_length = 15,field_alias = "Element Type")

            with arcpy.da.UpdateCursor(spatial_join,"element_type") as cursor:
                for row in cursor:
                    row[0] = shape_output
                    cursor.updateRow(row)

            arcpy.TableToTable_conversion(shape_output, r"H:\\temp\\temp.gdb", table_output)
