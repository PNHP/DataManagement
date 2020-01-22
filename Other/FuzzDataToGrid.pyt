#-------------------------------------------------------------------------------
# Name:        Fuzz Data to Grid Tool
# Purpose:     This tool takes user data and fuzzes it to a larger grid. A pre-existing grid can be used, or the user can enter specifications for a
#              new grid to be created. The output includes grid features attributed with the original input data information.
# Author:      Molly Moore
# Created:     01/10/2020
#-------------------------------------------------------------------------------

######################################################################################################################################################
## Import packages and define environment settings
######################################################################################################################################################

import arcpy,time,datetime,os,sys,string
from getpass import getuser

arcpy.env.overwriteOutput = True

######################################################################################################################################################
## Begin toolbox
######################################################################################################################################################

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the .pyt file)."""
        self.label = "Fuzz Data to Grid Tool v1.0"
        self.alias = "Fuzz Data to Grid Tool v1.0"
        self.tools = [GridData]

######################################################################################################################################################
## Begin create NHA tool - this tool creates the core and supporting NHAs and fills their initial attributes
######################################################################################################################################################

class GridData(object):
    def __init__(self):
        self.label = "Fuzz Data to Grid"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        input_data = arcpy.Parameter(
            displayName = "Input data to be fuzzed to a grid",
            name = "input_data",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        grid_exist = arcpy.Parameter(
            displayName = "Check here if you would like to use an existing grid (otherwise, this tool will create a grid for you according to the specifications entered below)",
            name = "grid_exist",
            datatype = "GPBoolean",
            parameterType = "Required",
            direction = "Input")
        grid_exist.value = "false"

        existing_grid = arcpy.Parameter(
            displayName = "Existing Grid",
            name = "site_desc",
            datatype = "GPFeatureLayer",
            parameterType = "Optional",
            direction = "Input")

##        extent = arcpy.Parameter(
##            displayName = "Extent of Grid (select feature layer or raster)",
##            name = "extent",
##            datatype = "GPFeatureLayer",
##            parameterType = "Optional",
##            direction = "Input")

        grid_shape = arcpy.Parameter(
            displayName = "Shape of Grid",
            name = "grid_shape",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")
        grid_shape.filter.type = "ValueList"
        grid_shape.filter.list = ["HEXAGON","SQUARE","TRIANGLE"]

        size = arcpy.Parameter(
            displayName = "Area of Planning Unit",
            name = "size",
            datatype = "GPArealUnit",
            parameterType = "Optional",
            direction = "Input")

        output_fields = arcpy.Parameter(
            displayName = "Fields to be Included in Output Fuzzed Data",
            name = "output_fields",
            datatype = "Field",
            parameterType = "Required",
            direction = "Input",
            multiValue = True)
        output_fields.filter.list = []

        output_grid = arcpy.Parameter(
            displayName = "Location and Name of Output Fuzzed Data",
            name = "output_grid",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Output")

        params = [input_data,grid_exist,existing_grid,grid_shape,size,output_fields,output_grid]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, params):
        if params[1].value == True:
            params[2].enabled = True
            params[3].enabled = False
            params[4].enabled = False
        else:
            params[2].enabled = False
            params[3].enabled = True
            params[4].enabled = True
        return

        for i in [0,2]:
            #check if parameter has been changed
            if not params[i].hasBeenValidated:
                #empty list to populate with fields
                flds = []
                #iterate both parameters
                for x in [0,2]:
                    #get parameter
                    fc = params[x].valueAsText
                    #check if parameter has been input
                    if fc:
                        #get input feature class fields and add to list
                        flds += [f.name for f in arcpy.ListFields (fc)]
                #update field input
                params[5].filter.list = flds

    def updateMessages(self, params):
        return

    def execute(self, params, messages):

        input_data = params[0].valueAsText
        grid_exist = params[1].valueAsText
        existing_grid = params[2].valueAsText
##        extent = params[3].valueAsText
        grid_shape = params[3].valueAsText
        size = params[4].valueAsText
        output_fields = params[5].valueAsText
        output_grid = params[6].valueAsText

        # set grid to either existing grid or generate grid from user input
        if grid_exist == "true":
            arcpy.AddMessage("Using existing grid.")
            grid = existing_grid
        else:
            arcpy.AddMessage("Creating new grid.")
            grid = arcpy.GenerateTessellation_management(os.path.join("in_memory","grid"),input_data,grid_shape,size)

        # create field map and add tables to field map
        fieldmappings = arcpy.FieldMappings()
        fieldmappings.addTable(input_data)
        fieldmappings.addTable(grid)

        output_fields = output_fields.split(";")
        output_fields.append("Shape")

        # remove all fields not in output_fields from field map
        for field in fieldmappings.fields:
            if field.name not in output_fields:
                fieldmappings.removeFieldMap(fieldmappings.findFieldMapIndex(field.name))

        # perform spatial join
        output = arcpy.SpatialJoin_analysis(grid,input_data,output_grid,"JOIN_ONE_TO_MANY","KEEP_COMMON",fieldmappings,"INTERSECT")
        # delete identical features
        arcpy.DeleteIdentical_management(output,output_fields)
        # delete join fields
        arcpy.DeleteField_management(output,["Join_Count","TARGET_FID","JOIN_FID"])
