#-------------------------------------------------------------------------------
# Name:        FIND Biotics Layer Creator
# Purpose:     This script is designed to take the biotics source points, lines, and
#              polys and return a single point feature class that includes source
#              points, and centroids of source lines and polygons. This script
#              should be run monthly after the Biotics update so that the output
#              can be added to the FIND feature services.
# Author:      Molly Moore
# Created:     2017-02-20
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

# set input parameters
biotics_database = r'W:\Heritage\Heritage_Data\Biotics_datasets.gdb' # biotics dataset
output_database = r'W:\To_Server\BioticsToFIND.gdb' # output database where centroids layer will be written
input_features = ['eo_sourceln', 'eo_sourcept', 'eo_sourcepy'] # feature class names of source lines, points, and polys
out_features = ['line', 'point', 'polygon'] # temporary centroid feature classes to be merged
output_feature = 'Biotics_SourceFeature_centroids_' + time.strftime("%Y%m%d") # filename of output centroid feature class

merge_features = [] # empty list that will hold paths of temporary centroid feature classes to be merged
# enter into zipped loop including biotics source features as input
for in_feature, out_feature in zip(input_features, out_features):
    biotics_feature = os.path.join(biotics_database, in_feature)
    # create centroids for all biotics source features
    output = arcpy.FeatureToPoint_management(biotics_feature, out_feature, "INSIDE")
    arcpy.AddField_management(output,"feature_type","TEXT","","",8,"Feature Type")
    with arcpy.da.UpdateCursor(output,"feature_type") as cursor:
        for row in cursor:
            row[0] = out_feature
            cursor.updateRow(row)
    # add path of temporary centroid feature classes to merge_features list
    merge_features.append(output)

# merge centroid feature classes into one Biotics source feature centroid feature class
arcpy.Merge_management(merge_features, os.path.join(output_database, output_feature))