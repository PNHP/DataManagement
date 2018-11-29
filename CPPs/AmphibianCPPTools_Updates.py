''''
Name:        Amphibian CPP Tools

Author:      B. Plunkett & K. Erath

Created:     Summer 2013
Updated:     10Dec2014

12/10/2014
Edited tool description.
10/8/2014
Replaced recordset layer with feature layer in parameter data types, so default value not required.
Update 3/6/2014
-Changed SYSTEM to WETLAND_TYPE and 'Lacustrine' to 'Lake' for SQL expression. New NWI layer has different attributes.
'''
# Import modules
import arcpy, time, datetime, cpp
from cpp import WatershedTool
from cpp import FrogCore

"""To enter default values, uncomment this block of code, change the pathnames to
the correct pathnames on your local computer, and uncomment the blocks of code
that start with 'Enter default values here'"""
### Create variables for default values
### These should all be in the WPC custom albers projection
##core_work_val = r"kerath_working\Core_kerath_working"
##slp_work_val = r"E:\CPP_package_2014_01_28\ConservationPlanningPolygon_package.gdb\Erath_Polys\Supporting_kerath_working"
##sfinputs_val = [r"E:\CPP_Layers.gdb\pre_ln", r"E:\CPP_Layers.gdb\pre_pt", r"E:\CPP_Layers.gdb\pre_py"]
##eoptreps_val = r"Biotics\eo_ptreps"
##huc12_val = r"E:\CPP_Layers.gdb\Watershed_HUC12"
##geol_val = r"E:\CPP_Layers.gdb\BedrockGeology"
##nwi_val = r"E:\CPP_Layers.gdb\National_Wetland_Inventory"
##floodplain_val = r"E:\CPP_Layers.gdb\Floodplains"


# Set tools to overwrite existing outputs
arcpy.env.overwriteOutput = True

class Toolbox(object):
    def __init__(self):
        self.label = "CPP Amphibians"
        self.alias = "Amphibians"

        #List of tool classes associated with this toolbox
        self.tools = [EasternHellbenderCore, MudpuppyCore, SouthernLeopardFrogCore, SouthernLeopardFrogSupporting, NorthernLeopardFrogCore, NorthernLeopardFrogSupporting, NorthernCricketFrogCore, NorthernCricketFrogSupporting, EasternSpadefootCore, EasternSpadefootSupporting, GreenSalamanderSupporting]

class EasternHellbenderCore(object):
    def __init__(self):
        self.label = "Eastern Hellbender Core"
        self.category = "Eastern Hellbender"
        self.specIDVersion = "Amphibians_Eastern_Hellbender_20130528"
        self.canRunInBackground = False
        self.description = """
        This tool generates a preliminary Eastern Hellbender CPP Core for the occurrence specified
        by the users EO_ID input value.

        """

    def getParameterInfo(self):

        eoptreps = arcpy.Parameter(
            displayName = "Selected EO record in eoptreps",
            name = "eoptreps",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        sfInputs = arcpy.Parameter(
            displayName = "Source Feature Inputs",
            name = "sfInputs",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input",
            multiValue = True)

        workingCoreInput = arcpy.Parameter(
            displayName = "Working Core",
            name = "workingCoreInput",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        wengerBuffer = arcpy.Parameter(
            displayName = "Wengerrd",
            name = "WengerBuffer",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

#-------Enter default values here:
##        eoptreps.value = eoptreps_val
##        sfInputs.value = sfinputs_val
##        workingCoreInput.value = core_work_val
##        wengerBuffer.value = Wengerrd

        params = [eoptreps, sfInputs, workingCoreInput, wengerBuffer]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, params):
        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):
        eoptreps = params[0].valueAsText
        sfInputs = params[1].valueAsText
        workingCoreInput = params[2].valueAsText
        wengerBuffer = params[3].valueAsText
        # Convert multivalue input to a python list
        sf_list = sfInputs.split(';')

        #Print the specification version id
        arcpy.AddMessage("\n********************************************************************\n\
        Script follows specification version: \n\
        {0}.\n\
        ********************************************************************\n".format(str(self.specIDVersion)))
        # Set the workspace environment
        arcpy.env.workspace = "in_memory"

        # Get eoid from eoptreps
        srows = arcpy.da.SearchCursor(eoptreps, ["EO_ID"])
        for srow in srows:
            eoid = srow[0]
            arcpy.AddMessage("Processing EO ID {0} at {1}".format(eoid, datetime.datetime.now().strftime("%H:%M:%S")))

            #Create an empty group for core features
            coreFeatures = []

            #Buffer the source features by 350 meters to create an occurrence buffer
            #that will be used to capture core features
            cpp.buffer_sfs(sf_list, eoid, "350 Meters", "occurBuff")
            arcpy.CopyFeatures_management("occurBuff", "OCCURRENCE")

            #Capture all wenger within the occurrence buffer
            arcpy.MakeFeatureLayer_management(wengerBuffer, "wengerLayer")
            arcpy.Clip_analysis("wengerLayer", "occurBuff", "eligibleWenger")
            coreFeatures.append("eligibleWenger")

            #Merge and apply a 400 meter buffer core features
            arcpy.Merge_management(coreFeatures, "featuresMerged")
            arcpy.Dissolve_management("featuresMerged", "prelimCore")

            #Create drawnNotes message
            notes = '"PRELIMINARY - remove tributaries if < 4 Strahler class, connect disjointed CPPs along same stem"'

            #Append to the workingCoreInput
            arcpy.Append_management("prelimCore", workingCoreInput, "NO_TEST")

            # Add eoid to core polygon and calculate attributes
            urows = arcpy.da.UpdateCursor(workingCoreInput, ["EO_ID"], '"EO_ID" is null')
            for urow in urows:
                urow[0] = eoid
                urows.updateRow(urow)
            #Calculate attributes
            cpp.calc_attr_core(eoid, eoptreps, workingCoreInput, self.specIDVersion, notes)

            #Clear the in_memory workspace
            arcpy.Delete_management("in_memory")

        return

class MudpuppyCore(object):
    def __init__(self):
        self.label = "Mudpuppy Core"
        self.category = "Mudpuppy"
        self.specIDVersion = "Amphibians_Mudpuppy_20130528"
        self.canRunInBackground = False
        self.description = """
        This tool generates a preliminary mudpuppy CPP Core for the occurrence specified
        by the users EO_ID input value.

        """

    def getParameterInfo(self):

        eoptreps = arcpy.Parameter(
            displayName = "Selected EO record in eoptreps",
            name = "eoptreps",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        sfInputs = arcpy.Parameter(
            displayName = "Source Feature Inputs",
            name = "sfInputs",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input",
            multiValue = True)

        workingCoreInput = arcpy.Parameter(
            displayName = "Working Core",
            name = "workingCoreInput",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        wengerBuffer = arcpy.Parameter(
            displayName = "Wengerrd",
            name = "WengerBuffer",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

#-------Enter default values here:
##        eoptreps.value = eoptreps_val
##        sfInputs.value = sfinputs_val
##        workingCoreInput.value = core_work_val
##        wengerBuffer.value = Wengerrd

        params = [eoptreps, sfInputs, workingCoreInput, wengerBuffer]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, params):
        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):
        eoptreps = params[0].valueAsText
        sfInputs = params[1].valueAsText
        workingCoreInput = params[2].valueAsText
        wengerBuffer = params[3].valueAsText
        # Convert multivalue input to a python list
        sf_list = sfInputs.split(';')

        #Print the specification version id
        arcpy.AddMessage("\n********************************************************************\n\
        Script follows specification version: \n\
        {0}.\n\
        ********************************************************************\n".format(str(self.specIDVersion)))
        # Set the workspace environment
        arcpy.env.workspace = "in_memory"

        # Get eoid from eoptreps
        srows = arcpy.da.SearchCursor(eoptreps, ["EO_ID"])
        for srow in srows:
            eoid = srow[0]
            arcpy.AddMessage("Processing EO ID {0} at {1}".format(eoid, datetime.datetime.now().strftime("%H:%M:%S")))

            #Create an empty group for core features
            coreFeatures = []

            #Buffer the source features by 350 meters to create an occurrence buffer
            #that will be used to capture core features
            cpp.buffer_sfs(sf_list, eoid, "350 Meters", "occurBuff")
            arcpy.CopyFeatures_management("occurBuff", "OCCURRENCE")

            #Capture all wenger within the occurrence buffer
            arcpy.MakeFeatureLayer_management(wengerBuffer, "wengerLayer")
            arcpy.Clip_analysis("wengerLayer", "occurBuff", "eligibleWenger")
            coreFeatures.append("eligibleWenger")

            #Merge and apply a 400 meter buffer core features
            arcpy.Merge_management(coreFeatures, "featuresMerged")
            arcpy.Dissolve_management("featuresMerged", "prelimCore")

            #Create drawnNotes message
            notes = '"PRELIMINARY - remove tributaries if < 3 Strahler class, connect disjointed CPPs along same stem"'

            #Append to the workingCoreInput
            arcpy.Append_management("prelimCore", workingCoreInput, "NO_TEST")

            # Add eoid to core polygon and calculate attributes
            urows = arcpy.da.UpdateCursor(workingCoreInput, ["EO_ID"], '"EO_ID" is null')
            for urow in urows:
                urow[0] = eoid
                urows.updateRow(urow)
            #Calculate attributes
            cpp.calc_attr_core(eoid, eoptreps, workingCoreInput, self.specIDVersion, notes)

            #Clear the in_memory workspace
            arcpy.Delete_management("in_memory")

        return

class SouthernLeopardFrogCore(FrogCore):
    def __init__(self):
        # Call the initialization method of the super class, FrogCore
        super(SouthernLeopardFrogCore, self).__init__()
        # Override label of superclass and add other properties
        self.label = "Southern Leopard Frog Core"
        self.category = "Southern Leopard Frog"
        self.specIDVersion = "Amphibians_Southern_Leopard_Frog_20130515"
        self.clip_distance = "3 Kilometers"
        self.buffer_distance = "500 Meters"
        self.notes = "PRELIMINARY - Remove urban and dense suburban areas, as well as multi-lane roadways"


class SouthernLeopardFrogSupporting(WatershedTool):
    def __init__(self):
        # Call the initialization method of the superclass, WatershedTool
        super(SouthernLeopardFrogSupporting, self).__init__()

        # Override label of superclass and add other properties
        self.label = "Southern Leopard Frog Supporting"
        self.category = "Southern Leopard Frog"
        self.specIDVersion = "Amphibians_Southern_Leopard_Frog_20130515"

    def execute(self, parameters, messages):
        """The source code of the tool."""
        # Define tool variables
        core = parameters[0].valueAsText
        lidar_gdb = parameters[1].valueAsText
        pa_county = parameters[2].valueAsText
        slp = parameters[3].valueAsText

        #Print the specification version id
        arcpy.AddMessage("\n********************************************************************\n\
        Script follows specification version: \n\
        {0}.\n\
        ********************************************************************\n".format(str(self.specIDVersion)))
        # Do not use in memory workspace for watershed tools, it causes errors and oddly shaped watersheds
        # If there is no workspace set in the tool, it will use the geoprocessing workspace environment of the map document
        # In CPP map project -> Geoprocessing -> Workspace

        # Run supporting watershed method of the super class
        self.supportingWatershed(core, slp, lidar_gdb, pa_county, min_distance = '120 Meters', spec_id = self.specIDVersion)
        return


class NorthernLeopardFrogCore(FrogCore):
    def __init__(self):
        # Call the initialization method of the super class, FrogCore
        super(NorthernLeopardFrogCore, self).__init__()
        # Override label of superclass and add other properties
        self.label = "Northern Leopard Frog Core"
        self.category = "Northern Leopard Frog"
        self.specIDVersion = "Amphibians_Northern_Leopard_Frog_20130225"
        self.clip_distance = "3 Kilometers"
        self.buffer_distance = "500 Meters"
        self.notes = "PRELIMINARY - Remove urban and dense suburban areas, as well as multi-lane roadways"


class NorthernLeopardFrogSupporting(WatershedTool):
    def __init__(self):
        # Call the initialization method of the superclass, WatershedTool
        super(NorthernLeopardFrogSupporting, self).__init__()

        # Override label of superclass and add other properties
        self.label = "Northern Leopard Frog Supporting"
        self.category = "Northern Leopard Frog"
        self.specIDVersion = "Amphibians_Northern_Leopard_Frog_20130225"

    def execute(self, parameters, messages):
        """The source code of the tool."""
        # Define tool variables
        core = parameters[0].valueAsText
        lidar_gdb = parameters[1].valueAsText
        pa_county = parameters[2].valueAsText
        slp = parameters[3].valueAsText

        #Print the specification version id
        arcpy.AddMessage("\n********************************************************************\n\
        Script follows specification version: \n\
        {0}.\n\
        ********************************************************************\n".format(str(self.specIDVersion)))
        # Do not use in memory workspace for watershed tools, it causes errors and oddly shaped watersheds
        # If there is no workspace set in the tool, it will use the geoprocessing workspace environment of the map document
        # In CPP map project -> Geoprocessing -> Workspace

        # Run supporting watershed method of the super class
        self.supportingWatershed(core, slp, lidar_gdb, pa_county, min_distance = '120 Meters', spec_id = self.specIDVersion)
        return


class NorthernCricketFrogCore(FrogCore):
    def __init__(self):
        # Call the initialization method of the super class, FrogCore
        super(NorthernCricketFrogCore, self).__init__()
        # Override label of superclass and add other properties
        self.label = "Northern Cricket Frog Core"
        self.category = "Northern Cricket Frog"
        self.specIDVersion = "Amphibians_Northern_Cricket_Frog_20130225"
        self.clip_distance = "1.3 Kilometers"
        self.buffer_distance = "1.3 Kilometers"
        self.notes = "PRELIMINARY - Remove multi-lane roadways"


class NorthernCricketFrogSupporting(WatershedTool):
    def __init__(self):
        # Call the initialization method of the superclass, WatershedTool
        super(NorthernCricketFrogSupporting, self).__init__()

        # Override label of superclass and add other properties
        self.label = "Northern Cricket Frog Supporting"
        self.category = "Northern Cricket Frog"
        self.specIDVersion = "Amphibians_Northern_Cricket_Frog_20130225"

    def execute(self, parameters, messages):
        """The source code of the tool."""
        # Define tool variables
        core = parameters[0].valueAsText
        lidar_gdb = parameters[1].valueAsText
        pa_county = parameters[2].valueAsText
        slp = parameters[3].valueAsText

        #Print the specification version id
        arcpy.AddMessage("\n********************************************************************\n\
        Script follows specification version: \n\
        {0}.\n\
        ********************************************************************\n".format(str(self.specIDVersion)))
        # Do not use in memory workspace for watershed tools, it causes errors and oddly shaped watersheds
        # If there is no workspace set in the tool, it will use the geoprocessing workspace environment of the map document
        # In CPP map project -> Geoprocessing -> Workspace

        # Run supporting watershed method of the super class
        self.supportingWatershed(core, slp, lidar_gdb, pa_county, min_distance = '120 Meters', spec_id = self.specIDVersion)
        return


class EasternSpadefootCore(object):
    def __init__(self):
        self.label = "Eastern Spadefoot Core"
        self.category = "Eastern Spadefoot"
        self.specIDVersion = "Amphibians_Eastern_Spadefoot_20130816"
        self.canRunInBackground = False
        self.description = """
        This tool generates an Eastern Spadefoot CPP Core for the occurrence specified
        by the users EO_ID input value. Additional processing may be required to combine
        other cores within 5 kilometers by surrounding them in a minimum convex polygon.

        REVIEW NOTES:
            The user must upload the output core to the 'CPP_Singles' geodatabase.
            Use the existing 'singles' records to join Eastern Spadefoot core that is within
            5 kilometers by creating a minimum convex polygon that surrounds them.

        """

    def getParameterInfo(self):

        eoptreps = arcpy.Parameter(
            displayName = "Selected EO record in eoptreps",
            name = "eoptreps",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        sfInputs = arcpy.Parameter(
            displayName = "Source Feature Inputs",
            name = "sfInputs",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input",
            multiValue = True)

        workingCoreInput = arcpy.Parameter(
            displayName = "Working Core",
            name = "workingCoreInput",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        floodplainInput = arcpy.Parameter(
            displayName = "Floodplain",
            name = "floodplainInput",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        wetlandInput = arcpy.Parameter(
            displayName = "Wetland",
            name = "wetlandInput",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        unmappedWetlandInput = arcpy.Parameter(
            displayName = "Unmapped Wetland",
            name = "unmappedWetlandInput",
            datatype = "GPFeatureLayer",
            parameterType = "Optional",
            direction = "Input",)

#-------Enter default values here:
##        eoptreps.value = eoptreps_val
##        sfInputs.value = sfinputs_val
##        workingCoreInput.value = core_work_val
##        floodplainInput.value = floodplain_val
##        wetlandInput.value = nwi_val

        params = [eoptreps, sfInputs, workingCoreInput, floodplainInput, wetlandInput, unmappedWetlandInput]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, params):
        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):
        eoptreps = params[0].valueAsText
        sfInputs = params[1].valueAsText
        workingCoreInput = params[2].valueAsText
        floodplainInput = params[3].valueAsText
        wetlandInput = params[4].valueAsText
        unmappedWetlandInput = params[5].valueAsText
        # Convert multivalue input to a python list
        sf_list = sfInputs.split(';')

        #Print the specification version id
        arcpy.AddMessage("\n********************************************************************\n\
        Script follows specification version: \n\
        {0}.\n\
        ********************************************************************\n".format(str(self.specIDVersion)))
        # Set the workspace environment
        arcpy.env.workspace = "in_memory"

        # Get eoid from eoptreps
        srows = arcpy.da.SearchCursor(eoptreps, ["EO_ID"])
        for srow in srows:
            eoid = srow[0]
            arcpy.AddMessage("Processing EO ID {0} at {1}".format(eoid, datetime.datetime.now().strftime("%H:%M:%S")))

            #Create an empty group for core features
            coreFeatures = []

            #Buffer the source features by 400 meters to create an occurrence buffer
            #that will be used to capture core features
            cpp.buffer_sfs(sf_list, eoid, "400 Meters", "occurBuff")
            arcpy.CopyFeatures_management("occurBuff", "OCCURRENCE")

            #Capture all floodplain within the occurrence buffer
            arcpy.MakeFeatureLayer_management(floodplainInput, "floodplainLayer")
            arcpy.Clip_analysis("floodplainLayer", "occurBuff", "eligibleFloodplain")
            coreFeatures.append("eligibleFloodplain")

            #Capture all wetland within the occurrence buffer
            #--- NWI wetland
            arcpy.MakeFeatureLayer_management(wetlandInput, "wetlandLayer", """NOT "WETLAND_TYPE" = 'Riverine'  AND NOT  "WETLAND_TYPE" = 'Lake'""")
            arcpy.Clip_analysis("wetlandLayer", "occurBuff", "eligibleWetland")
            # --- unmapped wetland
            if unmappedWetlandInput is '' or unmappedWetlandInput == None:
                pass
            else:
                arcpy.Clip_analysis(unmappedWetlandInput, "occurBuff", "unmappedWetClip")
                arcpy.Buffer_analysis("unmappedWetClip", "unmappedWetBuff", "100 meters")
                arcpy.Append_management("unmappedWetBuff", "eligibleWetland", "NO_tEST")
            coreFeatures.append("eligibleWetland")

            #Merge and apply a 400 meter buffer core features
            arcpy.Merge_management(coreFeatures, "featuresMerged")
            arcpy.Buffer_analysis("featuresMerged", "featuresBuff", "400 meters")
            arcpy.Dissolve_management("featuresBuff", "prelimCore")

            #Create drawnNotes message
            notes = '"PRELIMINARY - create min convex polygon around other cores within 5km and remove unsuitable habitat"'

            #Append to the workingCoreInput
            arcpy.Append_management("prelimCore", workingCoreInput, "NO_TEST")

            # Add eoid to core polygon and calculate attributes
            urows = arcpy.da.UpdateCursor(workingCoreInput, ["EO_ID"], '"EO_ID" is null')
            for urow in urows:
                urow[0] = eoid
                urows.updateRow(urow)
            #Calculate attributes
            cpp.calc_attr_core(eoid, eoptreps, workingCoreInput, self.specIDVersion, notes)

            #Clear the in_memory workspace
            arcpy.Delete_management("in_memory")

        return
#END OF EasternSpadefootCore CLASS

class EasternSpadefootSupporting(object):
    def __init__(self):
        self.label = "Eastern Spadefoot Supporting"
        self.category = "Eastern Spadefoot"
        self.specIDVersion = "Amphibians_Eastern_Spadefoot_20130816"
        self.canRunInBackground = False
        self.description = """
        This tool creates an Eastern Spadefoot CPP Supporting based on a core from an individual
        occurrence.  The supporting includes all HUC-12 watersheds that intersect the core.
        """

    def getParameterInfo(self):

        workingCoreInput = arcpy.Parameter(
            displayName = "Selected CPP Core",
            name = "workingCoreInput",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        workingSLPInput = arcpy.Parameter(
            displayName = "Working Supporting",
            name = "workingSLPInput",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        watershedInput = arcpy.Parameter(
            displayName = "Watershed",
            name = "watershedInput",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        params = [workingCoreInput, workingSLPInput, watershedInput]
        return params

    def execute(self, params, messages):
        workingCoreInput = params[0].valueAsText
        workingSLPInput = params[1].valueAsText
        watershedInput = params[2].valueAsText

        #Print the specification version id
        arcpy.AddMessage("\n********************************************************************\n\
        Script follows specification version: \n\
        {0}.\n\
        ********************************************************************\n".format(str(self.specIDVersion)))

        # Set the workspace environment
        arcpy.env.workspace = "in_memory"

        # Get eoid from core
        srows = arcpy.da.SearchCursor(workingCoreInput, ["EO_ID"])
        for srow in srows:
            eoid = srow[0]
            arcpy.AddMessage("Processing EO ID {0} at {1}".format(eoid, datetime.datetime.now().strftime("%H:%M:%S")))

            #Create EO_ID selection query
            eoidQuery = '"EO_ID" = {0}'.format(eoid)

            #Create a targetCore layer
            arcpy.MakeFeatureLayer_management(workingCoreInput, "targetCore", eoidQuery)

            #Capture all HUC-12 watersheds that intersect the target core
            arcpy.MakeFeatureLayer_management(watershedInput, "watershedLayer")
            arcpy.SelectLayerByLocation_management("watershedLayer", "INTERSECT", "targetCore")

            # Use feature to polygon tool to remove voids and dissolve to a single feature
            arcpy.FeatureToPolygon_management("watershedLayer", "features_to_polygon")
            arcpy.Dissolve_management("features_to_polygon", "newSLP")

            #Append to the workingSLPInput
            arcpy.Append_management("newSLP", workingSLPInput, "NO_TEST")

            # Add eoid to supporting polygon
            urows = arcpy.da.UpdateCursor(workingSLPInput, ["EO_ID"], '"EO_ID" is null')
            for urow in urows:
                urow[0] = eoid
                urows.updateRow(urow)
            # Calculate attributes
            cpp.calc_attr_slp(eoid, workingCoreInput, workingSLPInput, specid = self.specIDVersion)

            #Clear the in_memory workspace
            arcpy.Delete_management("in_memory")

        return
#END OF EasternSpadefootSupporting CLASS


class GreenSalamanderSupporting(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Green Salamander Supporting"
        self.description = """This tool creates a supporting polygon for the
        selected green salamander core.  'Mauch Chunk Formation' and  'Pottsville
        Formation' geology polygons are clipped by the HUC-12(s) containing the
        core and buffered by 200m. If the core is not completely contained within
        this polygon, then the core is buffered by 200m."""
        self.canRunInBackground = False
        self.category = "Green Salamander"
        self.specIDVersion = "Amphibians_Green_Salamander_20130815"

    def getParameterInfo(self):
        #Define parameter definitions

        # First parameter
        param0 = arcpy.Parameter(
            displayName="Selected CPP Core",
            name="core",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        # Second parameter
        param1 = arcpy.Parameter(
            displayName="HUC 12 Watersheds",
            name="huc12",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        # Third parameter
        param2 = arcpy.Parameter(
            displayName="PA Bedrock Geology (pagpoly)",
            name="pagpoly",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        # Fourth parameter
        param3 = arcpy.Parameter(
            displayName="Working Supporting Layer",
            name="slp",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

#-------Enter default values here:
##        param0.value = core_work_val
##        param1.value = huc12_val
##        param2.value = geol_val
##        param3.value = slp_work_val

        params = [param0, param1, param2, param3]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, params):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, params):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, params, messages):
        """The source code of the tool."""

        # Define tool variables
        core = params[0].valueAsText
        huc12 = params[1].valueAsText
        pagpoly = params[2].valueAsText
        slp = params[3].valueAsText

        #Print the specification version id
        arcpy.AddMessage("\n********************************************************************\n\
        Script follows specification version: \n\
        {0}.\n\
        ********************************************************************\n".format(str(self.specIDVersion)))

        # Set the workspace environment
        arcpy.env.workspace = "in_memory"

        # Get the eoid from the core layer
        srows = arcpy.da.SearchCursor(core, ["EO_ID"])
        for srow in srows:
            eoid = srow[0]
            arcpy.AddMessage("Processing EO ID {0} at {1}".format(eoid, datetime.datetime.now().strftime("%H:%M:%S")))

            # Create feature layers so selections will run, use query to ensure only
            # Mauch Chunk and Pottsville Sandstone Formations are included in the geology layer
            arcpy.MakeFeatureLayer_management(core, "core_lyr")
            arcpy.MakeFeatureLayer_management(huc12, "huc12_lyr")
            arcpy.MakeFeatureLayer_management(pagpoly, "pagpoly_lyr", "\"NAME\" in ('Mauch Chunk Formation', 'Pottsville Formation')")

            # Select the HUC-12(s) that intersect the core
            arcpy.SelectLayerByLocation_management("huc12_lyr", "INTERSECT", core)
            # Select pagpolys that intersect selected HUC-12(s) to speed the the clip process
            arcpy.SelectLayerByLocation_management("pagpoly_lyr", "INTERSECT", "huc12_lyr")
            # Clip pagpolys by HUC-12(s)
            arcpy.Clip_analysis("pagpoly_lyr", "huc12_lyr", "pagpoly_clip")
            # Buffer selected pagpoly by 200m
    ##        arcpy.Buffer_analysis("pagpoly_clip", "pagpoly_buffer", "200 METERS", "FULL", "ROUND", "ALL") # This does not work, memory error
            arcpy.Buffer_analysis("pagpoly_clip", "int_slp", "200 METERS") # This works

            # Determine if core is completely contained within the buffered geology polygons
            arcpy.MakeFeatureLayer_management("int_slp", "int_slp_lyr")
            # Add a 2m buffer to the core to make sure the slp edge does not align with the core
            # edge when viewed from a distance (this line added after PFBC polygon review in regards to EO ID 260)
            arcpy.Buffer_analysis(core, "core_2mbuff", "2 METERS")
            arcpy.SelectLayerByLocation_management("int_slp_lyr", "COMPLETELY_CONTAINS", "core_2mbuff")

            # If the supporting does not completely contain the core, buffer the
            # core by 200m and merge the buffer with the supporting polygon
            if int(arcpy.GetCount_management("int_slp_lyr").getOutput(0)) == 0:
                arcpy.Buffer_analysis("core_lyr", "core_200m", "200 Meters")
                arcpy.Append_management("core_200m", "int_slp_lyr", "NO_TEST")

            # Remove donut holes
            arcpy.FeatureToPolygon_management("int_slp", "int_slp_no_holes")

##            # Remove disjunct pieces
##            arcpy.MultipartToSinglepart_management("int_slp_no_holes", "int_slp_expl")
##            arcpy.MakeFeatureLayer_management("int_slp_expl", "int_slp_expl_lyr")
##            arcpy.SelectLayerByLocation_management("int_slp_expl_lyr", "INTERSECT", "core_lyr")
##            cpp.select_adjacent_features("int_slp_expl_lyr")
##            arcpy.CopyFeatures_management("int_slp_expl_lyr", "int_slp_contig")

            # Remove disjunct pieces (faster way)
            arcpy.Dissolve_management("int_slp_no_holes", "int_slp_diss", multi_part = "SINGLE_PART")
            arcpy.MakeFeatureLayer_management("int_slp_diss", "int_slp_lyr")
            arcpy.SelectLayerByLocation_management("int_slp_lyr", "INTERSECT", "core_lyr")
            arcpy.CopyFeatures_management("int_slp_lyr", "int_slp_contig")

            # Dissolve and append to supporting layer
            arcpy.Dissolve_management("int_slp_contig", "final_slp")
            arcpy.Append_management("final_slp", slp, "NO_TEST")

            # Update feature with null eoid in supporting layer
            urows = arcpy.da.UpdateCursor(slp, ["EO_ID"], '"EO_ID" is null')
            for urow in urows:
                urow[0] = eoid
                urows.updateRow(urow)

            # Calculate attributes
            cpp.calc_attr_slp(eoid, core, slp)

        return