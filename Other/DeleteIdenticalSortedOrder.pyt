# Import system modules
import arcpy

# set tools to overwrite existing outputs
arcpy.env.overwriteOutput = True
arcpy.env.workspace = "memory" # we will just make the environment workspace the memory workspace for now because I don't think we will need to use it.

# begin toolbox
class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the .pyt file)."""
        self.label = "Delete Identical by Sorted Order"
        self.alias = "Delete Identical by Sorted Order"
        self.canRunInBackground = False

        # List of tool classes associated with this toolbox
        self.tools = [DeleteDups]

class DeleteDups(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Delete Identical by Sorted Order Order"
        self.description = "Deletes records from a feature class or table that have identical values in a set of fields and keeps largest or smallest value based on user input sort field. If the geometry field (Shape) is selected as a field to evaluate for duplicates, feature geometries are compared."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        input_dataset = arcpy.Parameter(
            displayName="Dataset with duplicates to remove",
            name="input_dataset",
            datatype="GPTableView",
            parameterType="Required",
            direction="Input")

        group_field = arcpy.Parameter(
            displayName="Fields to evaluate for duplicates",
            name="group_field",
            datatype="Field",
            parameterType="Optional",
            multiValue= True,
            direction="Input")
        group_field.parameterDependencies = [input_dataset.name]

        sort_field = arcpy.Parameter(
            displayName="Sort field",
            name="sort_field",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        sort_field.parameterDependencies = [input_dataset.name]

        sort_direction = arcpy.Parameter(
            displayName="Sort direction",
            name="sort_direction",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        sort_direction.filter.type = "ValueList"
        sort_direction.filter.list = ["Ascending (keep the smallest number or oldest date)","Descending (keep the largest number or most recent date)"]

        output_fc = arcpy.Parameter(
            displayName="Output features",
            name="output_fc",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Output")

        params = [input_dataset, group_field, sort_field, sort_direction, output_fc]
        return params

    def execute(self, params, messages):
        # source code of the tool
        input_dataset = params[0].valueAsText
        group_field = params[1].valueAsText
        sort_field = params[2].valueAsText
        sort_direction = params[3].valueAsText
        output_fc = params[4].valueAsText

        group_fields = group_field.split(';')

        # define SQL sort direction based on user input
        if sort_direction == "Ascending (keep the smallest number or oldest date)":
            sort = "ASC"
        elif sort_direction == "Descending (keep the largest number or most recent date)":
            sort = "DESC"
        else:
            arcpy.AddMessage("Hmmm... Something is up with your sort direction...")

        # create copy of input feature class from which to delete features
        desc = arcpy.Describe(input_dataset)
        if desc.dataType == "FeatureClass" or desc.dataType == "FeatureLayer":
            output_fc = arcpy.ExportFeatures_conversion(input_dataset,output_fc)
        elif desc.dataType == "Table" or desc.dataType == "TableView":
            output_fc = arcpy.ExportTable_conversion(input_dataset,output_fc)
        else:
            arcpy.AddError("There is a problem with your input dataset.")
            sys.exit()

        # get list of all unique rows of field values from user input group fields
        groups = sorted({row for row in arcpy.da.SearchCursor(output_fc, group_fields)})
        # construct the sql order by statement to sort data
        sql_orderby = "ORDER BY {} {}".format(sort_field, sort)  # sql code to order by the chosen field
        # loop through each unique group of fields
        for group in groups:
            seen = set() # create set to store tuples in
            # enter update cursor with order by clause
            with arcpy.da.UpdateCursor(output_fc, group_fields, sql_clause=(None, sql_orderby)) as cursor:
                for row in cursor:
                    # turn row values into tuple
                    row = tuple(row)
                    # if the row is part of the unique group
                    if row == group:
                        # if row has already been added to the seen set, then delete the duplicate rows
                        if row in seen:
                            cursor.deleteRow()
                        # if row has NOT been added to the seen set yet, add first occurrence to the set
                        else:
                            seen.add(row)
