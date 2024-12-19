# -------------------------------------------------------------------------------
# Name:        Feature Query Exporter
# Purpose:     Allows users to input a csv file, select a column for query, and export features from an ArcGIS feature class that match those attributes.
#
# Author:      MMoore
#
# Created:     03/21/2022
# Copyright:   (c) MMoore 2022
# -------------------------------------------------------------------------------

# Import modules
import arcpy
import os
from arcpy.sa import *
import pandas as pd

# Set tools to overwrite existing outputs
arcpy.env.overwriteOutput = True
arcpy.env.workspace = "memory"

######################################################################################################################################################
## Begin toolbox
######################################################################################################################################################

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the .pyt file)."""
        self.label = "Feature Exporter"
        self.alias = "Feature Exporter"
        self.canRunInBackground = False
        self.tools = [CSVQueryExport]


######################################################################################################################################################
## Begin the CSVQueryExport tool that allows users to input a csv file, select a column for query, and export records that match those attributes.
######################################################################################################################################################

class CSVQueryExport(object):
    def __init__(self):
        self.label = "CSV Query Export"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        export_lyr = arcpy.Parameter(
            displayName="Export Layer (layer from which features will be exported)",
            name="export_lyr",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        export_query_fld = arcpy.Parameter(
            displayName="Query Field in Export Layer",
            name="export_query_fld",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        export_query_fld.parameterDependencies = [export_lyr.name]

        csv_tbl = arcpy.Parameter(
            displayName="CSV file that contains values for export query",
            name="csv",
            datatype="DEFile",
            parameterType="Required",
            direction="Input")

        csv_field = arcpy.Parameter(
            displayName="CSV field containing values for export query",
            name="csv_field",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        output_fc = arcpy.Parameter(
            displayName="Output Feature Class",
            name="output_fc",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        query_string = arcpy.Parameter(
            displayName="Check here if query list in .csv are numbers that should be read as strings",
            name="query_string",
            datatype="GPBoolean",
            parameterType="Required",
            direction="Input")

        params = [export_lyr, export_query_fld, csv_tbl, csv_field, output_fc, query_string]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, params):
        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):
        export_lyr = params[0].valueAsText
        export_query_field = params[1].valueAsText
        csv_tbl = params[2].valueAsText
        csv_field = params[3].valueAsText
        output_fc = params[4].valueAsText
        query_string = params[5].valueAsText

        df = pd.read_csv(csv_tbl, encoding = 'latin1')
        query_list = df["{}".format(csv_field)].values.tolist()

        if query_string:
            query_list = [str(x) for x in query_list]
        else:
            pass

        if arcpy.ListFields(export_lyr,export_query_field)[0].type == 'Integer' or arcpy.ListFields(export_lyr,export_query_field)[0].type == 'Double' or arcpy.ListFields(export_lyr,export_query_field)[0].type == 'Float':
            where_clause = "{} in {}".format(export_query_field,tuple(query_list))
        else:
            where_clause = "{} in ({})".format(export_query_field,','.join("'"+str(x)+"'" for x in query_list))

        # query_lyr = arcpy.MakeFeatureLayer_management(export_lyr,"query_lyr",where_clause=where_clause)

        output = arcpy.FeatureClassToFeatureClass_conversion(export_lyr,os.path.dirname(output_fc),os.path.basename(output_fc),where_clause=where_clause)

        with arcpy.da.SearchCursor(output,export_query_field) as cursor:
            output_ids = sorted({row[0] for row in cursor})

        output_df = pd.DataFrame(output_ids,columns=['exported_features'])

        merge = pd.merge(df,output_df[['exported_features']],left_on=csv_field,right_on='exported_features',how='outer')

        merge.to_csv(os.path.join(os.path.dirname(csv_tbl),os.path.basename(csv_tbl)+"_ExportedFeatures.csv"),index=False)