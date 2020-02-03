#-------------------------------------------------------------------------------
# Name:        FIND Negative Data Entry Tool (FINDNegativeDataEntryTool.pyt)
# Purpose:
# Author:      mmoore
# Created:     27/01/2020
#-------------------------------------------------------------------------------

######################################################################################################################################################
## Import packages and define environment settings
######################################################################################################################################################

import arcpy,time,datetime,os,sys,string
from getpass import getuser
from FIND_et_2019 import * # these need to be updated yearly with ET updates - use ET_to_PythonDictionary.py script to create dictionaries

arcpy.env.overwriteOutput = True

######################################################################################################################################################
## Begin toolbox
######################################################################################################################################################

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the .pyt file)."""
        self.label = "FIND Negative Data Entry Tool"
        self.alias = "FIND Negative Data Entry Tool"
        self.tools = [NegativeDataEntryTool]

######################################################################################################################################################
## Begin negative data entry tool
######################################################################################################################################################

class NegativeDataEntryTool(object):
    def __init__(self):
        self.label = "FIND Negative Data Entry Tool"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        survey_site = arcpy.Parameter(
            displayName = "Selected Survey Site Layer",
            name = "survey_site",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        ref_code = arcpy.Parameter(
            displayName = "Reference Code for Selected Survey Site",
            name = "ref_code",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input")

        element_type = arcpy.Parameter(
            displayName = "Element Type",
            name = "element_type",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input")
        element_type.filter.list = ["Insect","Lepidoptera","Other Invertebrate","Plant","Vertebrate Animal","Community"]

        element_name = arcpy.Parameter(
            displayName = "Element Name",
            name = "element_name",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input")

        not_found_comm = arcpy.Parameter(
            displayName = "Element Not Found Comments",
            name = "not_found_comm",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        params = [survey_site,ref_code,element_type,element_name,not_found_comm]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, params):
        # update choices for element name based on element type - uses the ET dictionaries
        if params[2].value == "Insect":
            params[3].filter.list = sorted(list(et_insect.values()))
        elif params[2].value == "Lepidoptera":
            params[3].filter.list = sorted(list(et_lep.values()))
        elif params[2].value == "Other Invertebrate":
            params[3].filter.list = sorted(list(et_invert.values()))
        elif params[2].value == "Plant":
            params[3].filter.list = sorted(list(et_plant.values()))
        elif params[2].value == "Vertebrate Animal":
            params[3].filter.list = sorted(list(et_vert.values()))
        elif params[2].value == "Community":
            params[3].filter.list = sorted(list(et_comm.values()))
        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):
        # define parameters
        survey_site = params[0].valueAsText
        ref_code = params[1].valueAsText
        element_type = params[2].valueAsText
        element_name = params[3].valueAsText
        not_found_comm = params[4].valueAsText

        # define element polygon layer and species list based on whether using ArcMap or ArcPro
        arc_prod = arcpy.GetInstallInfo()['ProductName']
        if arc_prod == 'ArcGISPro':
            elem_poly = r"FIND\Element Polygon"
        else:
            elem_poly = r"PNHP\FIND\Element Polygon"
        species_table = r"FIND.DBO.SpeciesList"

        # check that only one survey site is selected - error out if not
        desc = arcpy.Describe(survey_site)
        if desc.FIDSet == '':
            arcpy.AddError("No survey sites are selected. Please make a selection and try again.")
            sys.exit()
        if len((desc.FIDSet).split(';')) > 1:
            arcpy.AddError("More than one survey sites are selected. Please select only the survey site for which you intend to create a negative record and try again.")
            sys.exit()
        else:
            pass

        # get attributes from selected survey site to use later
        with arcpy.da.SearchCursor(survey_site,["refcode","survey_start","survey_end","SHAPE@"]) as cursor:
            for row in cursor:
                refcode = row[0]
                start = row[1]
                stop = row[2]
                geom = row[3]

        # check that user input reference code matches reference code of selected survey site
        if ref_code != refcode:
            arcpy.AddError("The reference code you entered does not match the reference code of your selected survey site. Please make sure you have selected the correct survey site and that your reference codes match and try again.")
            sys.exit()
        # check that reference code of selected survey site is not null
        elif refcode is None:
            arcpy.AddError("The reference code for your selected survey site is null. Please enter a valid reference code for your survey site and try again.")
            sys.exit()
        # check that reference code of selected survey site is the appropriate length
        elif len(refcode) != 8 and len(refcode) != 12:
            arcpy.AddError("The reference code for your selected survey site is invalid. The reference code must contain 8 or 12 characters (e.g. F20MOO01 or F20MOO01PAUS). Please enter a valid reference code and try again.")
            sys.exit()
        else:
            pass

        # assign domain key for element type to match domain in FIND and load in dictionary of ELSUBID and scientific names
        if element_type == "Insect":
            elem_type = 0
            d = et_insect
        elif element_type == "Lepidoptera":
            elem_type = 1
            d = et_lep
        elif element_type == "Other Invertebrate":
            elem_type = 2
            d = et_invert
        elif element_type == "Plant":
            elem_type = 3
            d = et_plant
        elif element_type == "Vertebrate Animal":
            elem_type = 4
            d = et_vert
        else:
            arcpy.AddError("Something went wrong and there is no element type!")
            sys.exit()

        # get element name from dictionary
        key_list = list(d.keys())
        val_list = list(d.values())
        elem_name = key_list[val_list.index(element_name)]

        # establish element found attribute as No because these are negative data
        elem_found = "N"

        # establish element found comments attribute to match user input
        elem_found_comm = not_found_comm

        # establish dm status as draft
        dm_stat = "dr"

        # insert new negative record into element polygon layer that matches shape of selected survey site
        values = [refcode,elem_type,elem_name,elem_found,elem_found_comm,start,stop,dm_stat,geom]
        fields = ["refcode","elem_type","elem_name","elem_found","elem_found_comm","date_start","date_stop","dm_stat","SHAPE@"]
        with arcpy.da.InsertCursor(elem_poly,fields) as cursor:
            cursor.insertRow(values)

        # insert new negative record into species list
        values = [elem_name,elem_found,refcode,element_name]
        fields = ["elem_name","elem_found","refcode","elem_name_archive"]
        with arcpy.da.InsertCursor(species_table,fields) as cursor:
            cursor.insertRow(values)

        # add status message for user
        arcpy.AddMessage("One negative species list record and element polygon were added to the survey "+refcode+" for the element: "+element_name)
        arcpy.AddWarning("Don't forget to mark your newly created element polygon Ready for DM once you make any necessary spatial or tabular updates.")