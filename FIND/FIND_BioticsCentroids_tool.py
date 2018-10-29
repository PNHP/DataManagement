#-------------------------------------------------------------------------------
# Name:        Biotics Centroids Creator
# Purpose:     This script is designed to take the biotics source points, lines, and
#              polys and return a single point feature class that includes source
#              points, and centroids of source lines and polygons. This script
#              should be run monthly after the Biotics update so that the output
#              can be added to the FIND feature services.
# Author:      Molly Moore
# Created:     2017-09-05
# Updated:
#
# To Do List/Future ideas:
#
#-------------------------------------------------------------------------------

# import system modules
import arcpy, os, datetime

# set tools to overwrite existing outputs
arcpy.env.overwriteOutput = True
# set environmental workspace to internal/temporary memory
arcpy.env.workspace = r'in_memory'

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Biotics Centroids Layer Creator"
        self.alias = "Biotics Centroids Layer Creator"

        # List of tool classes associated with this toolbox
        self.tools = [SF_centroids, EO_centroids]


class SF_centroids(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Source Feature Centroid Layer Creator"
        self.description = "Takes input points, lines, and polygons and creates a new source feature centroid layer."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        source_features = arcpy.Parameter(
            displayName = "Biotics source feature layers",
            name = "source_features",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input",
            multiValue = True)

        output_sf = arcpy.Parameter(
            displayName = "Output Source Feature Centroid Layer",
            name = "output_sf",
            datatype = "DEFeatureClass",
            parameterType = "Output",
            direction = "Output")

        params = [source_features, output_sf]
        return params

    def execute(self, params, messages):
        source_features = params[0].valueAsText
        output_sf = params[1].valueAsText
        sf_list = source_features.split(';')

        if len(sf_list) == 1:
            output_features = ["a"]
        elif len(sf_list) == 2:
            output_features = ["a", "b"]
        elif len(sf_list) == 3:
            output_features = ["a", "b", "c"]

        merge_features = []
        for sf, output in zip(sf_list, output_features):
            out = os.path.join("in_memory", output)
            # create centroids for all biotics source features
            output = arcpy.FeatureToPoint_management(sf, out, "INSIDE")
            # add path of temporary centroid feature classes to merge_features list
            merge_features.append(output)

        # merge centroid feature classes into one Biotics source feature centroid feature class
        arcpy.Merge_management(merge_features, output_sf)

        return

class EO_centroids(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "EO Reps Centroid Layer Creator"
        self.description = "Takes the EO Reps layer and creates EO Reps centroids layer."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        eo_reps = arcpy.Parameter(
            displayName = "Biotics EO reps layer",
            name = "eo_reps",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        output_eo = arcpy.Parameter(
            displayName = "Output EO Reps Centroid Layer",
            name = "output_eo",
            datatype = "DEFeatureClass",
            parameterType = "Required",
            direction = "Output")

        params = [eo_reps, output_eo]
        return params

    def execute(self, params, messages):
        eo_reps = params[0].valueAsText
        output_eo = params[1].valueAsText

        output = arcpy.FeatureToPoint_management(eo_reps, output_eo, "INSIDE")

        return