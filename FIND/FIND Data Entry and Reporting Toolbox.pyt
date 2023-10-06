"""-------------------------------------------------------------------------------
Name: FIND Data Entry and Reporting Toolbox
Purpose: Provide a suite of tools to aid in FIND data entry and reporting.
Author: mmoore
Created: 27/01/2020
Updated: 03/30/2021
Update Notes: 03/2021 - added Parcel and Contact Creator Tool, updated path names to FIND2021 feature service
Update Notes: 03/2022 - updated path names to FIND2022 feature service, updated parcel tool to better handle identical parcel features
12/2/2021 - BUG FIX: updated FIND table paths to be dependent on Pro version to solve issue of whether tables are nested under feature service or in standalone table section
#-------------------------------------------------------------------------------"""

######################################################################################################################################################
## Import packages and define environment settings
######################################################################################################################################################

import arcpy, datetime,os,sys
import csv
import shutil
from FIND_et_2023 import * # these need to be updated yearly with ET updates - use ET_to_PythonDictionary.py script to create dictionaries

arcpy.env.overwriteOutput = True

et_list = sorted(list(et_all.values()))
##et_list.insert(0," ")

pro_version = float(str(arcpy.GetInstallInfo()['Version'])[0:3])

######################################################################################################################################################
## Begin toolbox
######################################################################################################################################################

class Toolbox(object):
    def __init__(self):
        self.label = "FIND Data Entry and Reporting Toolbox"
        self.alias = "FIND Data Entry and Reporting Toolbox"
        self.tools = [NegativeDataEntryTool,PermissionDeniedTool,ListLoader,NeedsAttention,SpeciesLocator,ParcelContactCreator,SurveySiteReport]

######################################################################################################################################################
## Begin negative data entry tool
######################################################################################################################################################

class NegativeDataEntryTool(object):
    def __init__(self):
        self.label = "Negative Data Entry Tool"
        self.description = ""
        self.canRunInBackground = False
        self.category = "Data Entry Tools"

    def getParameterInfo(self):
        arcmap = arcpy.Parameter(
            displayName = "Check box if you are using ArcMap 10.xx instead of ArcGIS Pro.",
            name = "arcmap",
            datatype = "GPBoolean",
            parameterType = "optional",
            direction = "Input")

        survey_site = arcpy.Parameter(
            displayName = "Selected Survey Site Layer",
            name = "survey_site",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")
        survey_site.value = 'FIND\Survey Site'

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

        existing_eo = arcpy.Parameter(
            displayName = "If you were searching for an existing EO, what is the EO ID?",
            name = "existing_eo",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        not_found_comm = arcpy.Parameter(
            displayName = "Element Not Found Comments",
            name = "not_found_comm",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        params = [arcmap,survey_site,ref_code,element_type,element_name,existing_eo,not_found_comm]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, params):
        # update choices for element name based on element type - uses the ET dictionaries
        if params[3].value == "Insect":
            params[4].filter.list = sorted(list(et_insect.values()))
        elif params[3].value == "Lepidoptera":
            params[4].filter.list = sorted(list(et_lep.values()))
        elif params[3].value == "Other Invertebrate":
            params[4].filter.list = sorted(list(et_invert.values()))
        elif params[3].value == "Plant":
            params[4].filter.list = sorted(list(et_plant.values()))
        elif params[3].value == "Vertebrate Animal":
            params[4].filter.list = sorted(list(et_vert.values()))
        elif params[3].value == "Community":
            params[4].filter.list = sorted(list(et_comm.values()))

        if params[0].value == True:
            params[1].value = 'PNHP\FIND\Survey Site'
        else:
            params[1].value = 'FIND\Survey Site'

        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):
        # define parameters
        survey_site = params[1].valueAsText
        ref_code = params[2].valueAsText
        element_type = params[3].valueAsText
        element_name = params[4].valueAsText
        existing_eo = params[5].valueAsText
        not_found_comm = params[6].valueAsText

        # define element polygon layer and species list based on whether using ArcMap or ArcPro
        arc_prod = arcpy.GetInstallInfo()['ProductName']
        if arc_prod == 'ArcGISPro':
            elem_poly = r"FIND\Element Polygon"
        else:
            elem_poly = r"PNHP\FIND\Element Polygon"

        species_table = r"FIND\Species List"

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

        # eoid formatting
        if existing_eo:
            eoid = int(existing_eo)
        else:
            eoid = None

        # spatial feature capture method
        sp_feat_meth = "OTH"

        # spatial feature capture comments
        sp_feat_comm = "Feature copied from survey site using negative data entry tool."

        # insert new negative record into element polygon layer that matches shape of selected survey site
        values = [refcode,elem_type,elem_name,elem_found,elem_found_comm,eoid,start,stop,sp_feat_meth,sp_feat_comm,dm_stat,geom]
        fields = ["refcode","elem_type","elem_name","elem_found","elem_found_comm","eoid","date_start","date_stop","feat_meth","feat_meth_comm","dm_stat","SHAPE@"]
        with arcpy.da.InsertCursor(elem_poly,fields) as cursor:
            cursor.insertRow(values)

        # insert new negative record into species list
        values = [elem_name,elem_found,refcode,element_name]
        fields = ["elem_name","elem_found","refcode","elem_name_archive"]
        with arcpy.da.InsertCursor(species_table,fields) as cursor:
            cursor.insertRow(values)

        # add status message for user
        arcpy.AddMessage("One negative species list record and a negative element polygon were added to the survey "+refcode+" for the element: "+element_name+". DO NOT add this species record to your species list - it has already been added.")
        arcpy.AddWarning("Don't forget to mark your newly created element polygon Ready for DM once you make any necessary spatial or tabular updates.")

######################################################################################################################################################
## Begin permission denied data entry tool
######################################################################################################################################################

class PermissionDeniedTool(object):
    def __init__(self):
        self.label = "Permission Denied Data Entry Tool"
        self.alias = "Permission Denied Data Entry Tool"
        self.description = ""
        self.canRunInBackground = False
        self.category = "Data Entry Tools"

    def getParameterInfo(self):
        potential_site = arcpy.Parameter(
            displayName = "Selected Potential Survey Site Layer",
            name = "potential_site",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")
        potential_site.value = "FIND\Potential Survey Site"

        refcode = arcpy.Parameter(
            displayName = "Reference Code for Selected Survey Site (should start with P for personal reference)",
            name = "refcode",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input")

        parcel_id = arcpy.Parameter(
            displayName = "FIND Parcel ID if Available",
            name = "parcel_id",
            datatype = "GPString",
            parameterType= "Optional",
            direction = "Input"
        )

        target_elements = arcpy.Parameter(
            displayName = "Target Element(s) Name",
            name = "element_name",
            datatype = "GPValueTable",
            parameterType = "Optional",
            multiValue = True,
            direction = "Input")
        target_elements.columns = [['GPString','Target Element Type'],['GPString','Target Element'],['GPString','EO ID (if known)']]
        target_elements.filters[0].list = ["Insect","Lepidoptera","Other Invertebrate","Plant","Vertebrate Animal","Community"]
        target_elements.filters[1].list = et_list

        first_name = arcpy.Parameter(
            displayName = "Landowner/Contact First Name",
            name = "first_name",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        last_name = arcpy.Parameter(
            displayName = "Landowner/Contact Last Name",
            name = "last_name",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        position = arcpy.Parameter(
            displayName = "Contact position or relationship to parcel",
            name = "position",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        institution = arcpy.Parameter(
            displayName = "Institution or Organization",
            name = "institution",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        address = arcpy.Parameter(
            displayName = "Street Address",
            name = "address",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        city = arcpy.Parameter(
            displayName = "City",
            name = "city",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        state = arcpy.Parameter(
            displayName = "State",
            name = "state",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        zip_code = arcpy.Parameter(
            displayName = "Zip Code",
            name = "zip_code",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")
        mobile = arcpy.Parameter(
            displayName = "Mobile Phone (no symbols)",
            name = "mobile",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        landline = arcpy.Parameter(
            displayName = "Home Phone (no symbols)",
            name = "landline",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        email = arcpy.Parameter(
            displayName = "Email Address",
            name = "email",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        interaction = arcpy.Parameter(
            displayName = "Interaction Type",
            name = "interaction",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")
        interaction.filter.type = "ValueList"
        interaction.filter.list = ["Telephone","Email","In-Person","Letter or Postcard","Other"]

        pref_interaction = arcpy.Parameter(
            displayName = "Preferred Interaction Type",
            name = "pref_interaction",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")
        pref_interaction.filter.type = "ValueList"
        pref_interaction.filter.list = ["Telephone","Email","In-Person","Letter or Postcard","Other"]

        start_date = arcpy.Parameter(
            displayName = "Interaction Start Date",
            name = "start_date",
            datatype = "GPDate",
            parameterType = "Optional",
            direction = "Input")

        end_date = arcpy.Parameter(
            displayName = "Interaction End Date",
            name = "end_date",
            datatype = "GPDate",
            parameterType = "Optional",
            direction = "Input")

        int_comm = arcpy.Parameter(
            displayName = "Interaction Comments",
            name = "int_comm",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        permission = arcpy.Parameter(
            displayName = "Survey permission received?",
            name = "permission",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")
        permission.filter.type = "ValueList"
        permission.filter.list = ["Not Contacted","Contacted, Awaiting Response","Permission Denied","Permission Granted"]

        permission_comm = arcpy.Parameter(
            displayName = "Survey permission comments",
            name = "permission_comm",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        access = arcpy.Parameter(
            displayName = "Access Notes",
            name = "access",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        followup = arcpy.Parameter(
            displayName = "Follow Up Needed?",
            name = "followup",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")
        followup.filter.type = "ValueList"
        followup.filter.list = ["Yes","No"]

        followup_comm = arcpy.Parameter(
            displayName = "Follow Up Comments",
            name = "followup_comm",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        params = [potential_site,refcode,parcel_id,target_elements,first_name,last_name,position,institution,address,city,state,zip_code,mobile,landline,email,interaction,pref_interaction,start_date,end_date,int_comm,permission,permission_comm,access,followup,followup_comm]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, params):
        arc_prod = arcpy.GetInstallInfo()['ProductName']
        if arc_prod == 'ArcGISPro':
            params[0].value = 'FIND\Potential Survey Site'
        else:
            params[0].value = 'PNHP\FIND\Potential Survey Site'
        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):
        # define parameters
        potential_site = params[0].valueAsText
        refcode = params[1].valueAsText
        parcel_id = params[2].valueAsText
        target_elements = params[3].value
        first_name = params[4].valueAsText
        last_name = params[5].valueAsText
        position = params[6].valueAsText
        institution = params[7].valueAsText
        address = params[8].valueAsText
        city = params[9].valueAsText
        state = params[10].valueAsText
        zip_code = params[11].valueAsText
        mobile = params[12].valueAsText
        landline = params[13].valueAsText
        email = params[14].valueAsText
        interaction = params[15].valueAsText
        pref_interaction = params[16].valueAsText
        start_date = params[17].valueAsText
        end_date = params[18].valueAsText
        int_comm = params[19].valueAsText
        permission = params[20].valueAsText
        permission_comm = params[21].valueAsText
        access = params[22].valueAsText
        followup = params[23].valueAsText
        followup_comm = params[24].valueAsText

        # define element polygon layer and species list based on whether using ArcMap or ArcPro
        arc_prod = arcpy.GetInstallInfo()['ProductName']
        if arc_prod == 'ArcGISPro':
            elem_poly = r"FIND\Element Polygon"
        else:
            elem_poly = r"PNHP\FIND\Element Polygon"

        nf_target = r"FIND\Needs Found Table"
        contacts = r'FIND\Contacts'

        # check that only one survey site is selected - error out if not
        desc = arcpy.Describe(potential_site)
        if desc.FIDSet == '':
            arcpy.AddError("No potential survey sites are selected. Please make a selection and try again.")
            sys.exit()
        if len((desc.FIDSet).split(';')) > 1:
            arcpy.AddError("More than one potential survey sites are selected. Please select only the survey site for which you intend to create a negative record and try again.")
            sys.exit()
        else:
            pass

        # get attributes from selected survey site to use later
        with arcpy.da.SearchCursor(potential_site,["survey_name","SHAPE@","GlobalID"]) as cursor:
            for row in cursor:
                site_name = row[0]
                geom = row[1]
                GlobalID = row[2]

        # check that user input reference code matches reference code of selected survey site
        if site_name is None:
            arcpy.AddError("The site name for your selected potential survey site is null. Please make sure you have entered a site name for your proposed survey site and try again.")
            sys.exit()
        else:
            pass

        # insert new contact record
        if interaction == "Telephone":
            interaction = "TEL"
        elif interaction == "Email":
            interaction = "EMA"
        elif interaction == "In-Person":
            interaction = "PER"
        elif interaction == "Letter or Postcard":
            interaction = "LET"
        elif interaction == "Other":
            interaction = "OTH"
        else:
            pass

        if pref_interaction == "Telephone":
            pref_interaction = "TEL"
        elif pref_interaction == "Email":
            pref_interaction = "EMA"
        elif pref_interaction == "In-Person":
            pref_interaction = "PER"
        elif pref_interaction == "Letter or Postcard":
            pref_interaction = "LET"
        elif pref_interaction == "Other":
            pref_interaction = "OTH"
        else:
            pass

        if permission == "Not Contacted":
            permission = "NC"
        elif permission == "Contacted, Awaiting Response":
            permission = "AR"
        elif permission == "Permission Denied":
            permission = "PD"
        elif permission == "Permission Granted":
            permission = "PG"
        else:
            pass

        if followup == "Yes":
            followup = "Y"
        else:
            followup = "N"

        values = [refcode,site_name,parcel_id,first_name,last_name,position,institution,address,city,state,zip_code,mobile,landline,email,interaction,pref_interaction,start_date,end_date,int_comm,permission,permission_comm,access,followup,followup_comm,GlobalID]
        fields = ["refcode","prop_surv_site_n","parcelID","fname","lname","position","institution","address","city","state","zip","mphone","hphone","email","interaction_type","pref_interaction_type","date_start","date_end","interaction_comm","permission","permission_comm","access_notes","followup","followup_comm","pot_rel_GlobalID"]
        with arcpy.da.InsertCursor(contacts,fields) as cursor:
            cursor.insertRow(values)

        if target_elements:
            elems = []
            for element in target_elements:
                element_type = element[0]
                element_name = element[1]
                if element[2]:
                    eoid = int(element[2])
                else:
                    eoid = None
                # assign domain key for element type to match domain in FIND and load in dictionary of ELSUBID and scientific names
                if element_type == "Insect":
                    elem_type = 0
                elif element_type == "Lepidoptera":
                    elem_type = 1
                elif element_type == "Other Invertebrate":
                    elem_type = 2
                elif element_type == "Plant":
                    elem_type = 3
                elif element_type == "Vertebrate Animal":
                    elem_type = 4
                elif element_type == "Community":
                    elem_type = None
                else:
                    arcpy.AddError("Something went wrong and there is no element type!")
                    sys.exit()

                d = et_all
                # get element name from dictionary
                key_list = list(d.keys())
                val_list = list(d.values())
                elem_name = key_list[val_list.index(element_name)]

                # establish element found attribute as No because these are negative data
                elem_found = "N"

                # establish element found comments attribute to match user input
                elem_found_comm = "Permission for survey was denied."

                # establish dm status as draft
                dm_stat = "dr"

                # spatial feature capture method
                sp_feat_meth = "OTH"

                # spatial feature capture comments
                sp_feat_comm = "Feature copied from proposed survey site using permission denied data entry tool."

                # insert new negative record into element polygon layer that matches shape of selected survey site
                values = [refcode,elem_type,elem_name,elem_found,elem_found_comm,eoid,sp_feat_meth,sp_feat_comm,dm_stat,geom]
                fields = ["refcode","elem_type","elem_name","elem_found","elem_found_comm","eoid","feat_meth","feat_meth_comm","dm_stat","SHAPE@"]
                with arcpy.da.InsertCursor(elem_poly,fields) as cursor:
                    cursor.insertRow(values)

                # insert new negative record into nf species list
                values = [site_name,elem_type,elem_name]
                fields = ["survey_name","elem_type","elem_name"]
                with arcpy.da.InsertCursor(nf_target,fields) as cursor:
                    cursor.insertRow(values)

                elems.append(element_name)

                # add status message for user
            arcpy.AddMessage(str(len(target_elements))+" needs found species list record(s) and negative element polygon(s) were added to the proposed survey "+site_name+" for the element(s): "+', '.join(elems))
            arcpy.AddWarning("Don't forget to mark your newly created needs found element polygon(s) Ready for DM once you make any necessary spatial or tabular updates.")

        else:
            arcpy.AddMessage("No needs found species list record(s) or needs found element polygon(s) were added to the proposed survey "+site_name+" because you didn't list any!")

######################################################################################################################################################
## Begin ListLoader Tool
######################################################################################################################################################

class ListLoader(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "ListLoader for FIND"
        self.alias = "ListLoader for FIND"
        self.description = "Seamlessly loads species list data from ListMaster to FIND in ArcGIS Pro or ArcMap."
        self.canRunInBackground = False
        self.category = "Data Entry Tools"

    def getParameterInfo(self):
        return True

    def execute(self, parameters, messages):
        # define species list Excel file that was exported from ListMaster and the Species List table name
        sp_list = r'H:\specieslist_find.xls'
        sp_table = r"FIND\Species List"

        # convert the excel species list into a temporary ArcGIS table
        table = arcpy.ExcelToTable_conversion(sp_list, os.path.join("in_memory","tabled"), "out_SpeciesList")

        # get list of fields from species list table
        dsc = arcpy.Describe(table)
        fields = dsc.fields
        fieldnames = [field.name for field in fields if field.name != dsc.OIDFieldName]

        arcpy.AddMessage("The following species records were added to the FIND species list: ")
        # create search cursor for species list records and insert them into FIND species list
        with arcpy.da.SearchCursor(table,fieldnames) as sCur:
            with arcpy.da.InsertCursor(sp_table,fieldnames) as iCur:
                for row in sCur:
                    arcpy.AddMessage(row)
                    iCur.insertRow(row)
        return

######################################################################################################################################################
## Begin Needs Attention Reporting Tool
######################################################################################################################################################

class NeedsAttention(object):
    def __init__(self):
        self.label = "Needs Attention Report"
        self.alias = "Needs Attention Report"
        self.description = "Run this tool to generate a report of your incomplete records and make a selection on those records in the Element and Community Point, Line, Polygon, and Survey Site layers."
        self.canRunInBackground = False
        self.category = "QC and Reporting Tools"

    def getParameterInfo(self):
        last_name = arcpy.Parameter(
            displayName = "What's your last name?",
            name = "last_name",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input")

        params = [last_name]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, params):
        # update choices for element name based on element type - uses the ET dictionaries
        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):
        # define parameters
        last_name = params[0].valueAsText
        # establish location of .txt file report in same folder as script location
        txt_file = os.path.join(os.path.dirname(__file__),'FIND_NeedsAttentionReport.txt')

        # define name of parameters based on ArcGIS Pro or ArcMap
        arc_prod = arcpy.GetInstallInfo()['ProductName']
        if arc_prod == 'ArcGISPro':
            el_pt = r'FIND\Element Point'
            el_ln = r'FIND\Element Line'
            el_py = r'FIND\Element Polygon'
            cm_pt = r'FIND\Community or Other Point'
            cm_py = r'FIND\Community or Other Polygon'
            survey_site = r'FIND\Survey Site'
        else:
            el_pt = r'PNHP\FIND\Element Point'
            el_ln = r'PNHP\FIND\Element Line'
            el_py = r'PNHP\FIND\Element Polygon'
            cm_pt = r'PNHP\FIND\Community or Other Point'
            cm_py = r'PNHP\FIND\Community or Other Polygon'
            survey_site = r'PNHP\FIND\Survey Site'

        # get reference code initials from last name
        refcode_init = last_name.upper()[0:3]

        # print header to txt file
        now = datetime.datetime.now()
        dt_string = now.strftime("%m/%d/%y %I:%M:%p")
        with open(txt_file,'w') as f:
            f.write("################################################################"+"\n")
            f.write('\n')
            f.write("Welcome to the FIND Record Report!"+'\n')
            f.write("Updated: "+dt_string+'\n')
            f.write("\n")
            f.write("################################################################"+"\n")

        listo = [survey_site,el_pt,el_ln,el_py,cm_pt,cm_py]
        labels = ["Survey Site","Element Points","Element Lines","Element Polygons","Community Points","Community Polygons"]

        for l in listo:
            desc = arcpy.Describe(l)
            if desc.FIDSet == '':
                pass
            else:
                arcpy.AddWarning("Please clear all of your selections and try again.")
                sys.exit()

        # loop through layers to check for incomplete records and print results
        for l,x in zip(listo,labels):
            arcpy.SelectLayerByAttribute_management(l,"NEW_SELECTION","((refcode LIKE '%{}%') OR (created_user LIKE '%{}%')) AND (dm_stat <> 'dmproc' AND dm_stat <> 'dmready')".format(refcode_init, last_name))
            count = len(list(i for i in arcpy.da.SearchCursor(l, ["*"],where_clause = "((refcode LIKE '%{}%') OR (created_user LIKE '%{}%')) AND (dm_stat <> 'dmproc' AND dm_stat <> 'dmready')".format(refcode_init, last_name))))
            if count > 0:
                with open(txt_file,"a") as f:
                    f.write("\n")
                    f.write("You have "+str(count)+" incomplete records in the "+x+" layer:" + "\n")
                    f.write("\n")
                    f.write("Reference Code, DM Status, Created User, Created Date" + "\n")
                arcpy.AddWarning("You have "+str(count)+" incomplete records in the "+x+" layer.")
                with arcpy.da.SearchCursor(l,["refcode","dm_stat","created_user","created_date"],where_clause = "((refcode LIKE '%{}%') OR (created_user LIKE '%{}%')) AND (dm_stat <> 'dmproc' AND dm_stat <> 'dmready')".format(refcode_init, last_name)) as cursor:
                    for row in cursor:
                        with open(txt_file,'a') as f:
                            f.write(",  ".join(str(i) for i in row))
                            f.write("\n")
            else:
                with open(txt_file,'a') as f:
                    f.write('\n')
                    f.write("You do not have any incomplete records in the "+x+" layer. Congratulations!"+"\n")
                arcpy.AddWarning("You do not have any incomplete records in the "+x+" layer. Congratulations!")

            with open(txt_file,'a') as f:
                f.write("\n")
                f.write("################################################################"+"\n")

        os.startfile(txt_file)

######################################################################################################################################################
## Begin Species Locator Tool
######################################################################################################################################################

class SpeciesLocator(object):
    def __init__(self):
        self.label = "Species Locator Tool"
        self.alias = "Species Locator Tool"
        self.description = "Run this tool to select all survey site polygon within which the input species has/have been found."
        self.canRunInBackground = False
        self.category = "QC and Reporting Tools"

    def getParameterInfo(self):
        species = arcpy.Parameter(
            displayName = "What species would you like to locate?",
            name = "species",
            datatype = "GPString",
            multiValue = False,
            parameterType = "Required",
            direction = "Input")
        species.filter.list = sorted(list(et_all.values()))

        params = [species]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, params):
        # update choices for element name based on element type - uses the ET dictionaries
        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):
        # define parameters
        species = params[0].valueAsText

        # define name of parameters based on ArcGIS Pro or ArcMap
        arc_prod = arcpy.GetInstallInfo()['ProductName']
        if arc_prod == 'ArcGISPro':
            el_pt = r'FIND\Element Point'
            el_ln = r'FIND\Element Line'
            el_py = r'FIND\Element Polygon'
            cm_pt = r'FIND\Community or Other Point'
            cm_py = r'FIND\Community or Other Polygon'
            survey_site = r'FIND\Survey Site'
            ref_poly = r'FIND\Reference Area Polygon'
        else:
            el_pt = r'PNHP\FIND\Element Point'
            el_ln = r'PNHP\FIND\Element Line'
            el_py = r'PNHP\FIND\Element Polygon'
            cm_pt = r'PNHP\FIND\Community or Other Point'
            cm_py = r'PNHP\FIND\Community or Other Polygon'
            survey_site = r'PNHP\FIND\Survey Site'
            ref_poly = r'PNHP\FIND\Reference Area Polygon'

        species_list = r"FIND\Species List"
        ref_keyword = r"FIND\Reference Keyword Table"

        # create list of features to check for selections
        listo = [survey_site,el_pt,el_ln,el_py,cm_pt,cm_py]

        # check for selections and error out if there are any selections
        for l in listo:
            desc = arcpy.Describe(l)
            if desc.FIDSet == '':
                pass
            else:
                arcpy.AddWarning("Please clear all of your selections and try again.")
                sys.exit()

        d = et_all
        # get element name from dictionary
        key_list = list(d.keys())
        val_list = list(d.values())
        elem_list = key_list[val_list.index(species)]

        # get list of reference codes from species list, element/community points,lines,polys, and reference keyword table is species matches selection
        spec_presence = sorted({row[0] for row in arcpy.da.SearchCursor(species_list,['refcode','elem_name','elem_found']) if row[0] is not None and str(row[1])==str(elem_list) and row[2]!='N'and row[2]!='No'})
        el_pt_presence = sorted({row[0] for row in arcpy.da.SearchCursor(el_pt,['refcode','elem_name','elem_found']) if row[0] is not None and str(row[1])==str(elem_list) and row[2]!='N' and row[2]!='No'})
        el_ln_presence = sorted({row[0] for row in arcpy.da.SearchCursor(el_ln,['refcode','elem_name','elem_found']) if row[0] is not None and str(row[1])==str(elem_list) and row[2]!='N'and row[2]!='No'})
        el_py_presence = sorted({row[0] for row in arcpy.da.SearchCursor(el_py,['refcode','elem_name','elem_found']) if row[0] is not None and str(row[1])==str(elem_list) and row[2]!='N'and row[2]!='No'})
        cm_pt_presence = sorted({row[0] for row in arcpy.da.SearchCursor(cm_pt,['refcode','elem_name','elem_found']) if row[0] is not None and str(row[1])==str(elem_list) and row[2]!='N'and row[2]!='No'})
        cm_py_presence = sorted({row[0] for row in arcpy.da.SearchCursor(cm_py,['refcode','elem_name','elem_found']) if row[0] is not None and str(row[1])==str(elem_list) and row[2]!='N'and row[2]!='No'})
        ref_keyword_presence = sorted({row[0] for row in arcpy.da.SearchCursor(ref_keyword,['refcode','ref_keyword']) if row[0] is not None and row[1].lower() == species.lower()})

        # combine reference code lists
        refcode_list = spec_presence+el_pt_presence+el_ln_presence+el_py_presence+cm_pt_presence+cm_py_presence+ref_keyword_presence

        # create where clause based on number of reference codes in list
        if len(refcode_list)==0:
            arcpy.AddWarning("Your selected species was not found in any survey site :(")
            sys.exit()
        elif len(refcode_list)==1:
            where_clause = "refcode = '{}'".format(''.join(refcode_list))
        else:
            where_clause = 'refcode IN {0}'.format(tuple(refcode_list))

        # select survey site polygons and reference area polygons that match reference code in list
        arcpy.SelectLayerByAttribute_management(survey_site,"NEW_SELECTION",where_clause)
        arcpy.SelectLayerByAttribute_management(ref_poly,"NEW_SELECTION",where_clause)

        arcpy.AddMessage("The survey sites within which "+ species+ " has been found include: " + ', '.join(refcode_list))
        arcpy.AddMessage("The survey site(s) and/or reference area polygon(s) where " + species + " was found is(are) now selected.")

######################################################################################################################################################
## Begin Needs Attention Reporting Tool
######################################################################################################################################################

class ParcelContactCreator(object):
    def __init__(self):
        self.label = "Parcel and Contact Creator"
        self.alias = "Parcel and Contact Creator"
        self.description = "Use this tool to copy parcels into FIND and create a related contact record."
        self.canRunInBackground = False
        self.category = "Data Entry Tools"

    def getParameterInfo(self):
        parcel = arcpy.Parameter(
            displayName = "Selected Parcel Layer",
            name = "parcel",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        contact_include = arcpy.Parameter(
            displayName = "Check box if you want to create a related contact record",
            name = "contact_include",
            datatype = "GPBoolean",
            parameterType = "optional",
            direction = "Input")

        refcode = arcpy.Parameter(
            displayName = "Survey Site Reference Code",
            name = "refcode",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        prop_name = arcpy.Parameter(
            displayName = "Proposed Survey Site Name",
            name = "prop_name",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        attr_copy = arcpy.Parameter(
            displayName = "Check box if you want to copy attributes from the parcel layer to your contact record",
            name = "attr_copy",
            datatype = "GPBoolean",
            parameterType = "optional",
            direction = "Input")

        first_name = arcpy.Parameter(
            displayName = "Landowner/Contact First Name",
            name = "first_name",
            datatype = "Field",
            parameterType = "Optional",
            direction = "Input")
        first_name.parameterDependencies = [parcel.name]

        last_name = arcpy.Parameter(
            displayName = "Landowner/Contact Last Name",
            name = "last_name",
            datatype = "Field",
            parameterType = "Optional",
            direction = "Input")
        last_name.parameterDependencies = [parcel.name]

        position = arcpy.Parameter(
            displayName = "Contact position or relationship to parcel",
            name = "position",
            datatype = "Field",
            parameterType = "Optional",
            direction = "Input")
        position.parameterDependencies = [parcel.name]

        institution = arcpy.Parameter(
            displayName = "Institution or Organization",
            name = "institution",
            datatype = "Field",
            parameterType = "Optional",
            direction = "Input")
        institution.parameterDependencies = [parcel.name]

        address = arcpy.Parameter(
            displayName = "Street Address",
            name = "address",
            datatype = "Field",
            parameterType = "Optional",
            direction = "Input")
        address.parameterDependencies = [parcel.name]

        city = arcpy.Parameter(
            displayName = "City",
            name = "city",
            datatype = "Field",
            parameterType = "Optional",
            direction = "Input")
        city.parameterDependencies = [parcel.name]

        state = arcpy.Parameter(
            displayName = "State",
            name = "state",
            datatype = "Field",
            parameterType = "Optional",
            direction = "Input")
        state.parameterDependencies = [parcel.name]

        zip_code = arcpy.Parameter(
            displayName = "Zip Code",
            name = "zip_code",
            datatype = "Field",
            parameterType = "Optional",
            direction = "Input")
        zip_code.parameterDependencies = [parcel.name]

        first_name1 = arcpy.Parameter(
            displayName = "Landowner/Contact First Name",
            name = "first_name1",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        last_name1 = arcpy.Parameter(
            displayName = "Landowner/Contact Last Name",
            name = "last_name1",
            datatype = "Field",
            parameterType = "Optional",
            direction = "Input")

        position1 = arcpy.Parameter(
            displayName = "Contact position or relationship to parcel",
            name = "position1",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        institution1 = arcpy.Parameter(
            displayName = "Institution or Organization",
            name = "institution1",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        address1 = arcpy.Parameter(
            displayName = "Street Address",
            name = "address1",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        city1 = arcpy.Parameter(
            displayName = "City",
            name = "city1",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        state1 = arcpy.Parameter(
            displayName = "State",
            name = "state1",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        zip_code1 = arcpy.Parameter(
            displayName = "Zip Code",
            name = "zip_code1",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        mobile = arcpy.Parameter(
            displayName = "Mobile Phone (no symbols)",
            name = "mobile",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        landline = arcpy.Parameter(
            displayName = "Home Phone (no symbols)",
            name = "landline",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        email = arcpy.Parameter(
            displayName = "Email Address",
            name = "email",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        interaction = arcpy.Parameter(
            displayName = "Interaction Type",
            name = "interaction",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")
        interaction.filter.type = "ValueList"
        interaction.filter.list = ["Telephone","Email","In-Person","Letter or Postcard","Other"]

        pref_interaction = arcpy.Parameter(
            displayName = "Preferred Interaction Type",
            name = "pref_interaction",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")
        pref_interaction.filter.type = "ValueList"
        pref_interaction.filter.list = ["Telephone","Email","In-Person","Letter or Postcard","Other"]

        start_date = arcpy.Parameter(
            displayName = "Interaction Start Date",
            name = "start_date",
            datatype = "GPDate",
            parameterType = "Optional",
            direction = "Input")

        end_date = arcpy.Parameter(
            displayName = "Interaction End Date",
            name = "end_date",
            datatype = "GPDate",
            parameterType = "Optional",
            direction = "Input")

        int_comm = arcpy.Parameter(
            displayName = "Interaction Comments",
            name = "int_comm",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        permission = arcpy.Parameter(
            displayName = "Survey permission received?",
            name = "permission",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")
        permission.filter.type = "ValueList"
        permission.filter.list = ["Not Contacted","Contacted, Awaiting Response","Permission Denied","Permission Granted"]

        permission_comm = arcpy.Parameter(
            displayName = "Survey permission comments",
            name = "permission_comm",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        access = arcpy.Parameter(
            displayName = "Access Notes",
            name = "access",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        followup = arcpy.Parameter(
            displayName = "Follow Up Needed?",
            name = "followup",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")
        followup.filter.type = "ValueList"
        followup.filter.list = ["Yes","No"]

        followup_comm = arcpy.Parameter(
            displayName = "Follow Up Comments",
            name = "followup_comm",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        params = [parcel,contact_include,refcode,prop_name,attr_copy,first_name,last_name,position,institution,address,city,state,zip_code,
        first_name1,last_name1,position1,institution1,address1,city1,state1,zip_code1,
        mobile,landline,email,interaction,pref_interaction,start_date,end_date,int_comm,permission,permission_comm,access,followup,followup_comm]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, params):
        # update choices based on checkboxes
        if params[1].value == True:
            params[2].enabled = True
            params[3].enabled = True
            params[4].enabled = False
            params[21].enabled = True
            params[22].enabled = True
            params[23].enabled = True
            params[24].enabled = True
            params[25].enabled = True
            params[26].enabled = True
            params[27].enabled = True
            params[28].enabled = True
            params[29].enabled = True
            params[30].enabled = True
            params[31].enabled = True
            params[32].enabled = True
            params[33].enabled = True
            # if params[4].value == True:
            #     params[5].enabled = True
            #     params[6].enabled = True
            #     params[7].enabled = True
            #     params[8].enabled = True
            #     params[9].enabled = True
            #     params[10].enabled = True
            #     params[11].enabled = True
            #     params[12].enabled = True
            #     params[13].enabled = False
            #     params[14].enabled = False
            #     params[15].enabled = False
            #     params[16].enabled = False
            #     params[17].enabled = False
            #     params[18].enabled = False
            #     params[19].enabled = False
            #     params[20].enabled = False

            # else:
            #     params[5].enabled = False
            #     params[6].enabled = False
            #     params[7].enabled = False
            #     params[8].enabled = False
            #     params[9].enabled = False
            #     params[10].enabled = False
            #     params[11].enabled = False
            #     params[12].enabled = False
            params[13].enabled = True
            params[14].enabled = True
            params[15].enabled = True
            params[16].enabled = True
            params[17].enabled = True
            params[18].enabled = True
            params[19].enabled = True
            params[20].enabled = True
        else:
            params[2].enabled = False
            params[3].enabled = False
            params[4].enabled = False
            params[5].enabled = False
            params[6].enabled = False
            params[7].enabled = False
            params[8].enabled = False
            params[9].enabled = False
            params[10].enabled = False
            params[11].enabled = False
            params[12].enabled = False
            params[13].enabled = False
            params[14].enabled = False
            params[15].enabled = False
            params[16].enabled = False
            params[17].enabled = False
            params[18].enabled = False
            params[19].enabled = False
            params[20].enabled = False
            params[21].enabled = False
            params[22].enabled = False
            params[23].enabled = False
            params[24].enabled = False
            params[25].enabled = False
            params[26].enabled = False
            params[27].enabled = False
            params[28].enabled = False
            params[29].enabled = False
            params[30].enabled = False
            params[31].enabled = False
            params[32].enabled = False
            params[33].enabled = False
        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):
        # define parameters
        parcel = params[0].valueAsText
        contact_include = params[1].value
        if contact_include == True:
            refcode = params[2].valueAsText
            prop_name = params[3].valueAsText
            attr_copy = params[4].valueAsText
            mobile = params[21].valueAsText
            landline = params[22].valueAsText
            email = params[23].valueAsText
            interaction = params[24].valueAsText
            pref_interaction = params[25].valueAsText
            start_date = params[26].valueAsText
            end_date = params[27].valueAsText
            int_comm = params[28].valueAsText
            permission = params[29].valueAsText
            permission_comm = params[30].valueAsText
            access = params[31].valueAsText
            followup = params[32].valueAsText
            followup_comm = params[33].valueAsText
            # if attr_copy == False:
            first_name = params[13].valueAsText
            last_name = params[14].valueAsText
            position = params[15].valueAsText
            institution = params[16].valueAsText
            address = params[17].valueAsText
            city = params[18].valueAsText
            state = params[19].valueAsText
            zip_code = params[20].valueAsText

            # else:
            #     arcpy.AddMessage("things are working as they should")
            #     f_name = params[5].valueAsText
            #     l_name = params[6].valueAsText
            #     posit = params[7].valueAsText
            #     instit = params[8].valueAsText
            #     addr = params[9].valueAsText
            #     cit = params[10].valueAsText
            #     stat = params[11].valueAsText
            #     zip_c = params[12].valueAsText
            #
            #     with arcpy.da.SearchCursor(parcel,[f_name,l_name,posit,instit,addr,cit,stat,zip_c]) as cursor:
            #         for row in cursor:
            #             first_name = row[0]
            #             last_name = row[1]
            #             position = row[2]
            #             institution = row[3]
            #             address = row[4]
            #             city = row[5]
            #             state = row[6]
            #             zip_code = row[7]

        # define name of parameters based on ArcGIS Pro or ArcMap
        arc_prod = arcpy.GetInstallInfo()['ProductName']
        if arc_prod == 'ArcGISPro':
            find_parcels = r'FIND\Parcels'

        else:
            find_parcels = r'PNHP\FIND\Parcels'

        contacts = r'FIND\Contacts'

        # check that only one parcel is selected - error out if not
        desc = arcpy.Describe(parcel)
        if desc.FIDSet == '':
            arcpy.AddMessage("No parcels are selected. Please make a selection and try again.")
            sys.exit()
        elif len((desc.FIDSet).split(';')) > 1:
            arcpy.AddMessage("More than one parcel is selected. Please select only the parcel for which you intend to copy and try again.")
            sys.exit()
        else:
            pass

        # select FIND parcel if it is exactly identical in geometry to selected parcel
        with arcpy.da.SearchCursor(parcel,'SHAPE@') as cursor:
            for row in cursor:
                geom = row[0]
        counter = 0
        with arcpy.da.SearchCursor(find_parcels,['SHAPE@','parcelID']) as cursor:
            for row in cursor:
                if row[0] == geom:
                    counter += 1
                    parcel_id = row[1]

        # if no FIND parcels match geometry, copy parcel into FIND parcel layer and assign new parcel id
        if counter == 0:
            arcpy.SelectLayerByAttribute_management(find_parcels,"CLEAR_SELECTION")
            with arcpy.da.SearchCursor(find_parcels, 'parcelID') as cursor:
                existing_ids = sorted({row[0] for row in cursor})
            t = existing_ids[-1]
            parcel_id = "P-"+str(int(t[2:])+1).zfill(10)

            with arcpy.da.SearchCursor(parcel,"SHAPE@") as cursor:
                for row in cursor:
                    geom = row[0]

            values = [parcel_id,geom]
            fields = ["parcelID","SHAPE@"]
            with arcpy.da.InsertCursor(find_parcels,fields) as cursor:
                cursor.insertRow(values)
            arcpy.AddMessage("A new parcel was created in the FIND Parcels layer with Parcel ID: " +parcel_id)
        # if FIND parcel already exists, assign existing parcel ID
        elif counter == 1:
            arcpy.AddMessage("An identical parcel already exists in the FIND Parcels layer. Your contact record will be added to Parcel ID: "+ parcel_id)
        # if more than one identical FIND parcels exist
        else:
            arcpy.AddWarning("There are more than one identical parcels in FIND already. This is strange. Please contact the database administrator.")
            sys.exit()

        # check for user option to create contact
        if contact_include == True:

            # change selections into the coded domain values
            if interaction == "Telephone":
                interaction = "TEL"
            elif interaction == "Email":
                interaction = "EMA"
            elif interaction == "In-Person":
                interaction = "PER"
            elif interaction == "Letter or Postcard":
                interaction = "LET"
            elif interaction == "Other":
                interaction = "OTH"
            else:
                pass

            if pref_interaction == "Telephone":
                pref_interaction = "TEL"
            elif pref_interaction == "Email":
                pref_interaction = "EMA"
            elif pref_interaction == "In-Person":
                pref_interaction = "PER"
            elif pref_interaction == "Letter or Postcard":
                pref_interaction = "LET"
            elif pref_interaction == "Other":
                pref_interaction = "OTH"
            else:
                pass

            if permission == "Not Contacted":
                permission = "NC"
            elif permission == "Contacted, Awaiting Response":
                permission = "AR"
            elif permission == "Permission Denied":
                permission = "PD"
            elif permission == "Permission Granted":
                permission = "PG"
            else:
                pass

            if followup == "Yes":
                followup = "Y"
            else:
                followup = "N"

            # insert new contact record
            values = [parcel_id,refcode,prop_name,first_name,last_name,position,institution,address,city,state,zip_code,mobile,landline,email,interaction,pref_interaction,start_date,end_date,int_comm,permission,permission_comm,access,followup,followup_comm]
            fields = ["parcelID","refcode","prop_surv_site_n","fname","lname","position","institution","address","city","state","zip","mphone","hphone","email","interaction_type","pref_interaction_type","date_start","date_end","interaction_comm","permission","permission_comm","access_notes","followup","followup_comm"]
            with arcpy.da.InsertCursor(contacts,fields) as cursor:
                cursor.insertRow(values)

            arcpy.AddMessage("A new contact record was created with parcel ID: " + parcel_id + ". Please check this record, make any tabular updates, and save your edits.")

######################################################################################################################################################
## Begin Survey Site Report Tool
######################################################################################################################################################

class SurveySiteReport(object):
    def __init__(self):
        self.label = "Survey Site Report - DEVELOPMENT"
        self.alias = "Survey Site Report - DEVELOPMENT"
        self.description = "Run this tool to generate text that can be used to paste into a survey site report."
        self.canRunInBackground = False
        self.category = "QC and Reporting Tools"

    def getParameterInfo(self):
        survey_site = arcpy.Parameter(
            displayName = "Selected Survey Site Layer",
            name = "survey_site",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        params = [survey_site]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, params):
        # update choices for element name based on element type - uses the ET dictionaries
        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):
        # define parameters
        survey_site = params[0].valueAsText

        count = int(arcpy.GetCount_management(survey_site).getOutput(0))

        if count > 1:
            arcpy.AddWarning("Please select 1 and only 1 survey site and try again.")
            sys.exit()
        else:
            pass

        with arcpy.da.SearchCursor(survey_site,"survey_sit") as cursor:
            for row in cursor:
                if row[0] is None:
                    arcpy.AddWarning("Your survey site doesn't have a name. Please add a name in the 'Survey Site' field and try again.")
                    sys.exit()
                else:
                    survey_name = row[0]

        # establish location of .txt file report in same folder as script location
        name = str(''.join(x for x in survey_name if x.isalnum()))
        out_dir = os.path.join(os.path.dirname(__file__),'FIND_SurveyReports',name)
        if os.path.exists(out_dir):
            shutil.rmtree(out_dir)
        os.makedirs(out_dir)
        txt_file = os.path.join(out_dir,name+'.txt')

        # define name of parameters - this will only work in ArcGIS Pro v2.9 or above
        el_pt = r'FIND\Element Point'
        el_ln = r'FIND\Element Line'
        el_py = r'FIND\Element Polygon'
        cm_pt = r'FIND\Community or Other Point'
        cm_py = r'FIND\Community or Other Polygon'
        species_list = r'FIND\Species List'
        contact_list = r'FIND\Contacts'
        et = r'W:\\Heritage\\Heritage_Data\\Biotics_datasets.gdb\\ET'

        with arcpy.da.SearchCursor(survey_site,['refcode','survey_start','survey_end','surveyors','survey_typ','survey_typ_comm','site_desc','disturb','threats']) as cursor:
            for row in cursor:
                refcode = row[0]
                survey_start = row[1]
                survey_end = row[2]
                surveyors = row[3]
                survey_type = row[4]
                survey_type_comm = row[5]
                site_desc = row[6]
                disturb = row[7]
                threats = row[8]

        element_list = [el_pt,el_ln,el_py,cm_pt,cm_py]
        elem_dict = {}
        global_ids = []
        key_id = 1
        for elem in element_list:
            with arcpy.da.SearchCursor(elem,["refcode","elem_name","elem_found","eo_rank","direc_elem","GlobalID"]) as cursor:
                for row in cursor:
                    if row[0] == refcode:
                        elem_dict[key_id] = [int(row[1]),row[2],row[3],row[4]]
                        global_ids.append(row[5])
                        key_id += 1

        with arcpy.da.SearchCursor(et,["ELSUBID","SNAME","SCOMNAME","SPROT","PBSSTATUS","EO_TRACK"]) as cursor:
            for row in cursor:
                for k,i in elem_dict.items():
                    if i[0] == row[0]:
                        elem_dict[k].append(row[1])
                        elem_dict[k].append(row[2])
                        elem_dict[k].append(row[3])
                        elem_dict[k].append(row[4])
                        elem_dict[k].append(row[5])

        dups = []
        elem_dict_nodups = {}
        for key, val in elem_dict.items():
            if val not in dups:
                dups.append(val)
                elem_dict_nodups[key] = val

        for key, item in sorted(elem_dict_nodups.items()):
            if item[6] == 'PE':
                status = 'Endangered'
            elif item[6] == 'PT':
                status = 'Threatened'
            elif item[6] == 'PR':
                status = 'Rare'
            elif item[6] == 'PV':
                status = 'Vulnerable'
            elif item[7] == 'W' or item[7] == 'WATCH':
                status = 'Watch list'
            elif item[7] == 'TU':
                status = 'Undetermined'
            elif item[7] == 'PE':
                status = 'Endangered (proposed)'
            elif item[7] == 'PT':
                status = 'Threatened (proposed)'
            elif item[7] == 'PR':
                status = 'Rare (proposed)'
            elif item[7] == 'PV':
                status = 'Vulnerable (proposed)'
            elif item[7] == 'PX':
                status = 'Extirpated'
            elif item[8] == 'W':
                status = 'Watch list'
            else:
                status = item[6]
            elem_dict_nodups[key].append(status)

        elem_dict_filter = {}
        for key, item in sorted(elem_dict_nodups.items()):
            elem_dict_filter[key] = [item[5], item[4], item[1], item[9], item[2], item[3]]
        for key, item in elem_dict_filter.items():
            for x in range(6):
                if item[x] is None:
                    item[x] = '--'

        landowners = []
        with arcpy.da.SearchCursor(contact_list,["refcode","fname","lname"]) as cursor:
            for row in cursor:
                if row[0] == refcode:
                    landowners.append(row[1]+" "+row[2])

        species_dict = {}
        with arcpy.da.SearchCursor(species_list,["refcode","elem_name","elem_found"]) as cursor:
            for row in cursor:
                if row[0] == refcode and row[2] != 'N':
                    species_dict[int(row[1])] = []

        with arcpy.da.SearchCursor(et, ["ELSUBID","SNAME","SCOMNAME","EO_TRACK"]) as cursor:
            for row in cursor:
                for k, i in species_dict.items():
                    if k == row[0]:
                        species_dict[k].append(row[1])
                        species_dict[k].append(row[2])
                        if row[3] == 'N':
                            species_dict[k].append('No')
                        elif row[3] == 'Y':
                            species_dict[k].append('Yes')
                        elif row[3] == 'W':
                            species_dict[k].append('Watch')
                        else:
                            species_dict[k].append(row[3])

        species_dict_filter = {k: v for k, v in species_dict.items() if len(v) != 0}

        date_string = survey_start.strftime("%m/%d/%Y")
        if survey_end is not None and survey_start != survey_end:
            date_string = date_string+" - "+survey_end.strftime("%m/%d/%Y")
        if survey_type == "QUAL":
            survey_type = "Qualitative"
        elif survey_type == "QUAN":
            survey_type = "Quantitative"
        else:
            survey_type = ""
        if survey_type_comm is not None and survey_type != "":
            survey_type = survey_type + " - " + survey_type_comm
        else:
            survey_type = survey_type_comm

        with open(txt_file,'w') as f:
            f.write("SURVEY NAME"+"\n")
            f.write(survey_name+"\n")
            f.write("\n")
            f.write("LANDOWNER(S)"+"\n")
            f.write(", ".join(landowners)+"\n\n")
            f.write("SURVEY DATE"+"\n")
            f.write(date_string+"\n\n")
            f.write("SURVEYORS"+"\n")
            f.write(surveyors+"\n\n")
            f.write("SITE DESCRIPTION"+"\n")
            f.write(site_desc+"\n\n")
            f.write("SURVEY TYPE"+"\n")
            f.write(survey_type+"\n\n")
            f.write("THREATS AND RECOMMENDATIONS"+"\n")
            f.write(threats +"\n\n")

        os.startfile(txt_file)

        # write element list to .csv file
        with open(os.path.join(out_dir,'FIND_ElementList_'+name+'.csv'), 'w', newline='') as csvfile:
            csv_output = csv.writer(csvfile)
            # write heading rows to .csv
            csv_output.writerow(['Common Name','Latin Name','Found?','State Status','Population Rank*','Where Found'])
            # write dictionary rows to .csv
            for key in sorted(elem_dict_filter.keys()):
                csv_output.writerow(elem_dict_filter[key])

        os.startfile(os.path.join(out_dir,'FIND_ElementList_'+name+'.csv'))

        # write species list to .csv file
        with open(os.path.join(out_dir,'FIND_SpeciesList_'+name+'.csv'), 'w', newline='') as csvfile:
            csv_output = csv.writer(csvfile)
            # write heading rows to .csv
            csv_output.writerow(['Latin Name','Common Name','Species tracked?'])
            # write dictionary rows to .csv
            for key in sorted(species_dict_filter.keys()):
                csv_output.writerow(species_dict_filter[key])

        os.startfile(os.path.join(out_dir,'FIND_SpeciesList_'+name+'.csv'))

        for elem in element_list:
            with arcpy.da.SearchCursor(elem, ['DATA','ATT_NAME','ATTACHMENTID','REL_GLOBALID']) as cursor:
                for row in cursor:
                    if row[3] in global_ids:
                        attachment = row[0]
                        filenum = "ATT" + str(row[2]) + "_"
                        filename = filenum + str(row[1])
                        open(fileLocation + os.sep + filename, 'wb').write(attachment.tobytes())
