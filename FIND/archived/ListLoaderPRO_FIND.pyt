#-------------------------------------------------------------------------------
# Name:        ListLoader_FIND
# Purpose:     Updated FIND ListLoader tool for use with ArcGIS Pro
#
# Author:      M. Moore
#
# Created:     2019-11-25
# Updated:
#-------------------------------------------------------------------------------

# import modules
import arcpy, os

# Set tools to overwrite existing outputs
arcpy.env.overwriteOutput = True

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "ListLoaderPRO_FIND"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [LISTLOADERFIND]


class LISTLOADERFIND(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "ListLoader PRO for FIND"
        self.alias = "ListLoader PRO for FIND"
        self.description = "Seamlessly loads species list data from ListMaster to FIND in ArcGIS Pro."
        self.canRunInBackground = False

    def execute(self, parameters, messages):
        # define species list Excel file that was exported from ListMaster and the Species List table name
        sp_list = r'H:\specieslist_find.xls'
        sp_table = "FIND.DBO.SpeciesList"

        # convert the excel species list into a temporary ArcGIS table
        table = arcpy.ExcelToTable_conversion(sp_list, os.path.join("in_memory","table"), "out_SpeciesList")

        # get list of fields from species list table
        dsc = arcpy.Describe(table)
        fields = dsc.fields
        fieldnames = [field.name for field in fields if field.name != dsc.OIDFieldName]

        # create search cursor for species list records and insert them into FIND species list
        with arcpy.da.SearchCursor(table,fieldnames) as sCur:
            with arcpy.da.InsertCursor(sp_table,fieldnames) as iCur:
                for row in sCur:
                    iCur.insertRow(row)
        return