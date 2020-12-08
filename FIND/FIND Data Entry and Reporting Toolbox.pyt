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
from FIND_et_2020 import * # these need to be updated yearly with ET updates - use ET_to_PythonDictionary.py script to create dictionaries

arcpy.env.overwriteOutput = True

et_list = sorted(list(et_all.values()))
##et_list.insert(0," ")

######################################################################################################################################################
## Begin toolbox
######################################################################################################################################################

class Toolbox(object):
    def __init__(self):
        self.label = "FIND Data Entry and Reporting Toolbox"
        self.alias = "FIND Data Entry and Reporting Toolbox"
        self.tools = [NegativeDataEntryTool,PermissionDeniedTool,ListLoader,NeedsAttention,SpeciesLocator]

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
        arcmap = arcpy.Parameter(
            displayName = "Check box if you are using ArcMap 10.xx instead of ArcGIS Pro.",
            name = "arcmap",
            datatype = "GPBoolean",
            parameterType = "optional",
            direction = "Input")

        potential_site = arcpy.Parameter(
            displayName = "Selected Potential Survey Site Layer",
            name = "potential_site",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")
        potential_site.value = "FIND\Potential Survey Site"

        ref_code = arcpy.Parameter(
            displayName = "Reference Code for Selected Survey Site (should start with P for personal reference)",
            name = "ref_code",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input")

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

        last_name = arcpy.Parameter(
            displayName = "Landowner Last Name",
            name = "last_name",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        first_name = arcpy.Parameter(
            displayName = "Landowner First Name",
            name = "first_name",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        position = arcpy.Parameter(
            displayName = "Job Title of Landowner",
            name = "position",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        institution = arcpy.Parameter(
            displayName = "Landowner Institution",
            name = "institution",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        address = arcpy.Parameter(
            displayName = "Landowner Street Address",
            name = "address",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        city = arcpy.Parameter(
            displayName = "Landowner City",
            name = "city",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        state = arcpy.Parameter(
            displayName = "Landowner State",
            name = "state",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        zip_code = arcpy.Parameter(
            displayName = "Landowner Zip Code",
            name = "zip_code",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        landline = arcpy.Parameter(
            displayName = "Landowner Landline Phone (no symbols)",
            name = "landline",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        mobile = arcpy.Parameter(
            displayName = "Landowner Mobile Phone (no symbols)",
            name = "mobile",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        email = arcpy.Parameter(
            displayName = "Landowner E-mail Address",
            name = "email",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        maj_landowner = arcpy.Parameter(
            displayName = "Is this landowner the majority landowner?",
            name = "maj_landowner",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")

        contact_comm = arcpy.Parameter(
            displayName = "Landowner Contact Comments",
            name = "contact_comm",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input")

        params = [arcmap,potential_site,ref_code,target_elements,last_name,first_name,position,institution,address,city,state,zip_code,landline,mobile,email,maj_landowner,contact_comm]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, params):
        if params[0] == False:
            params[1].value = 'FIND\Potential Survey Site'
        elif params[0] == True:
            params[1].value = 'PNHP\FIND\Potential Survey Site'
        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):
        # define parameters
        potential_site = params[1].valueAsText
        ref_code = params[2].valueAsText
        target_elements = params[3].value
        last_name = params[4].valueAsText
        first_name = params[5].valueAsText
        position = params[6].valueAsText
        institution = params[7].valueAsText
        address = params[8].valueAsText
        city = params[9].valueAsText
        state = params[10].valueAsText
        zip_code = params[11].valueAsText
        landline = params[12].valueAsText
        mobile = params[13].valueAsText
        email = params[14].valueAsText
        maj_landowner = params[15].valueAsText
        contact_comm = params[16].valueAsText

        # define element polygon layer and species list based on whether using ArcMap or ArcPro
        arc_prod = arcpy.GetInstallInfo()['ProductName']
        if arc_prod == 'ArcGISPro':
            elem_poly = r"FIND\Element Polygon"
        else:
            elem_poly = r"PNHP\FIND\Element Polygon"
        nf_target = r"FIND.DBO.nf_target"
        contact_tbl = r"FIND.DBO.contact"

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
        with arcpy.da.SearchCursor(potential_site,["prop_surv_site_n","SHAPE@"]) as cursor:
            for row in cursor:
                site_name = row[0]
                geom = row[1]

        # check that user input reference code matches reference code of selected survey site
        if site_name is None:
            arcpy.AddError("The site name for your selected potential survey site is null. Please make sure you have entered a site name for your proposed survey site and try again.")
            sys.exit()
        else:
            pass

        # insert new negative record into element polygon layer that matches shape of selected survey site
        values = [last_name,first_name,position,institution,address,city,state,zip_code,landline,mobile,email,maj_landowner,contact_comm,"ng",ref_code,site_name]
        fields = ["lastn","firstn","position","instn","add1","city","st","zip","landline","mobile_ph","email","maj_landowner","contact_comm","perm_let_resp_type","refcode","prop_surv_site_n"]
        with arcpy.da.InsertCursor(contact_tbl,fields) as cursor:
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
                values = [ref_code,elem_type,elem_name,elem_found,elem_found_comm,eoid,sp_feat_meth,sp_feat_comm,dm_stat,geom]
                fields = ["refcode","elem_type","elem_name","elem_found","elem_found_comm","eoid","feat_meth","feat_meth_comm","dm_stat","SHAPE@"]
                with arcpy.da.InsertCursor(elem_poly,fields) as cursor:
                    cursor.insertRow(values)

                # insert new negative record into nf species list
                values = [site_name,elem_type,elem_name,"nc"]
                fields = ["prop_surv_site_n","target_type","target_el","survey_status"]
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
        sp_table = "FIND.DBO.SpeciesList"

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
## Begin Needs Attention Reporting Tool
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
        else:
            el_pt = r'PNHP\FIND\Element Point'
            el_ln = r'PNHP\FIND\Element Line'
            el_py = r'PNHP\FIND\Element Polygon'
            cm_pt = r'PNHP\FIND\Community or Other Point'
            cm_py = r'PNHP\FIND\Community or Other Polygon'
            survey_site = r'PNHP\FIND\Survey Site'

        species_list = r'FIND.DBO.SpeciesList'

        listo = [survey_site,el_pt,el_ln,el_py,cm_pt,cm_py]

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

        spec_presence = sorted({row[0] for row in arcpy.da.SearchCursor(species_list,['refcode','elem_name','elem_found']) if row[0] is not None and str(row[1])==str(elem_list) and row[2]!='N'and row[2]!='No'})
        el_pt_presence = sorted({row[0] for row in arcpy.da.SearchCursor(el_pt,['refcode','elem_name','elem_found']) if row[0] is not None and str(row[1])==str(elem_list) and row[2]!='N' and row[2]!='No'})
        el_ln_presence = sorted({row[0] for row in arcpy.da.SearchCursor(el_ln,['refcode','elem_name','elem_found']) if row[0] is not None and str(row[1])==str(elem_list) and row[2]!='N'and row[2]!='No'})
        el_py_presence = sorted({row[0] for row in arcpy.da.SearchCursor(el_py,['refcode','elem_name','elem_found']) if row[0] is not None and str(row[1])==str(elem_list) and row[2]!='N'and row[2]!='No'})
        cm_pt_presence = sorted({row[0] for row in arcpy.da.SearchCursor(cm_pt,['refcode','elem_name','elem_found']) if row[0] is not None and str(row[1])==str(elem_list) and row[2]!='N'and row[2]!='No'})
        cm_py_presence = sorted({row[0] for row in arcpy.da.SearchCursor(cm_py,['refcode','elem_name','elem_found']) if row[0] is not None and str(row[1])==str(elem_list) and row[2]!='N'and row[2]!='No'})

        refcode_list = spec_presence+el_pt_presence+el_ln_presence+el_py_presence+cm_pt_presence+cm_py_presence

        if len(refcode_list)==0:
            arcpy.AddWarning("Your selected species was not found in any survey site :(")
            sys.exit()
        elif len(refcode_list)==1:
            where_clause = "refcode = '{}'".format(''.join(refcode_list))
        else:
            where_clause = 'refcode IN {0}'.format(tuple(refcode_list))

        arcpy.SelectLayerByAttribute_management(survey_site,"NEW_SELECTION",where_clause)

        arcpy.AddMessage("The survey sites within which "+ species+ " has been found include: " + ', '.join(refcode_list))
        arcpy.AddMessage("The survey site(s) where " + species + " was found is(are) now selected.")


