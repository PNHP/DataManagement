# Import system modules
import arcpy

# set tools to overwrite existing outputs
arcpy.env.overwriteOutput = True
arcpy.env.workspace = "memory" # we will just make the environment workspace the memory workspace for now because I don't think we will need to use it.

# begin toolbox
class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the .pyt file)."""
        self.label = "Delete Duplicate Spatial Features" # I changed the name so this can be more generic than just for the net/trap captures. It should work with any dataset.
        self.alias = "Delete Duplicate Spatial Features"
        self.canRunInBackground = False

        # List of tool classes associated with this toolbox
        self.tools = [DeleteDups]

class DeleteDups(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Delete Duplicate Spatial Features"
        self.description = "This tool deletes duplicate spatial features."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        input_dataset = arcpy.Parameter(
            displayName="Dataset With Duplicates",
            name="input_dataset", # this should be same as the parameter name that you define
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        sort_field = arcpy.Parameter(
            displayName="Sort Field",
            name="sort_field",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        sort_field.parameterDependencies = [input_dataset.name]

        sort_direction = arcpy.Parameter(
            displayName="Sort Direction",
            name="sort_direction",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        sort_direction.filter.type = "ValueList"
        sort_direction.filter.list = ["Ascending (keep the smallest number or oldest date)","Descending (keep the largest number or most recent date)"]

        output_fc = arcpy.Parameter(
            displayName="Output Features",
            name="output_fc",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Output")

        params = [input_dataset, sort_field, sort_direction, output_fc]
        return params

    def execute(self, params, messages):
        # source code of the tool
        input_dataset = params[0].valueAsText # these need to match your parameter names that you defined under the parameters section.
        sort_field = params[1].valueAsText
        sort_direction = params[2].valueAsText
        output_fc = params[3].valueAsText

        # define parameters
        max_field = sort_field  # define field to sort within groups
        if sort_direction == "Ascending (keep the smallest number or oldest date)":
            sort = "ASC"
        elif sort_direction == "Descending (keep the largest number or most recent date)":
            sort = "DESC"
        else:
            arcpy.AddMessage("Hmmm... Something is up with your sort direction...")

        output_fc = arcpy.ExportFeatures_conversion(input_dataset,output_fc) # the cursor does not create a new feature class, so we need to export the features to a new feature class first

        sql_orderby = "ORDER BY {} {}".format(max_field,sort)  # sql code to order by the chosen field
        seen = []
        with arcpy.da.UpdateCursor(output_fc, "SHAPE@", sql_clause=(None, sql_orderby)) as cursor:
            for row in cursor:
                if row[0] in seen:
                    cursor.deleteRow()
                else:
                    seen.append(row[0])
