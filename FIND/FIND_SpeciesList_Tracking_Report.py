#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      MMoore
#
# Created:     15/02/2021
# Copyright:   (c) MMoore 2021
# Licence:     <your licence>
#-------------------------------------------------------------------------------

import pandas, os, arcpy
import numpy as np

elementGDB = r"C:\\Users\\MMoore\\AppData\\Roaming\\Esri\\ArcGISPro\\Favorites\\FIND2021.Working.pgh-gis0.sde"
species_list = os.path.join(elementGDB,'FIND2021.DBO.SpeciesList')
et = r'C:\\Users\\MMoore\\AppData\\Roaming\\Esri\\ArcGISPro\\Favorites\\PNHP.Working.pgh-gis0.sde\\PNHP.DBO.ET'
el_pt = os.path.join(elementGDB,'FIND2021\\Element Point')
el_ln = os.path.join(elementGDB,'FIND2021\\Element Line')
el_py = os.path.join(elementGDB,'FIND2021\\Element Polygon')
cm_pt = os.path.join(elementGDB,'FIND2021\\Community or Other Point')
cm_py = os.path.join(elementGDB,'FIND2021\\Community or Other Polygon')

def feature_class_to_pandas_df(feature_class,field_list):
    return pandas.DataFrame(
        arcpy.da.FeatureClassToNumPyArray(
            in_table = feature_class,
            field_names = field_list,
            skip_nulls = False,
            null_value = -99999
        )
    )

species_list_df = feature_class_to_pandas_df(species_list,["elem_name","refcode"])
et_df = feature_class_to_pandas_df(et,["ELSUBID","SNAME","SCOMNAME","EO_TRACK"])
species_list_df['elem_name'] = species_list_df['elem_name'].astype(str).astype(int)
et_df['ELSUBID'] = et_df['ELSUBID'].astype(int)

sp_list = species_list_df.merge(et_df,how='left',left_on='elem_name',right_on='ELSUBID')
sp_list_tracked = sp_list[(sp_list['EO_TRACK']=='Y')| (sp_list['EO_TRACK']=='W')]

el_pt_df = feature_class_to_pandas_df(el_pt,["elem_name","refcode"])
el_ln_df = feature_class_to_pandas_df(el_ln,["elem_name","refcode"])
el_py_df = feature_class_to_pandas_df(el_py,["elem_name","refcode"])
cm_pt_df = feature_class_to_pandas_df(cm_pt,["elem_name","refcode"])
cm_py_df = feature_class_to_pandas_df(cm_py,["elem_name","refcode"])

elements_df = pandas.concat([el_pt_df,el_ln_df,el_py_df,cm_pt_df,cm_py_df])
elements_df['elem_name'] = elements_df['elem_name'].astype(str).astype(int)
elements_df['refcode'] = elements_df['refcode'].astype(str)

common = sp_list_tracked.merge(elements_df,on=['elem_name','refcode'])
needs_created = sp_list_tracked[(~sp_list_tracked.elem_name.isin(common.elem_name))&(~sp_list_tracked.refcode.isin(common.refcode))]
needs_created.drop('ELSUBID',axis=1)

needs_created.to_csv(path_or_buf=r'H:\\temp\\needs_created.csv', sep=',')





##et_dict = {row[0]:int(row[1]) for row in arcpy.da.SearchCursor("ET",["SNAME","ELSUBID"])}
##
##with arcpy.da.UpdateCursor("",["elem_name"]) as cursor:
##    for row in cursor:
##        for k,v in et_dict.items():
##            if k==row[0]:
##                row[0] = int(v)
##                cursor.updateRow(row)
##


