#-------------------------------------------------------------------------------
# Name:        module2
# Purpose:
#
# Author:      mmoore
#
# Created:     22/11/2019
# Copyright:   (c) mmoore 2019
# Licence:     <your licence>
#-------------------------------------------------------------------------------

import os, subprocess
import pandas as pd
import sys

def install(package):
    subprocess.call([sys.executable, "-m", 'pip', 'install', package])

install('pyodbc')
import pyodbc

refcodes = "F19MOOTEST1".split(';')
#refcodes = arcpy.GetParameterAsText(0).split(';')
accessdb = r"P:\Conservation Programs\Natural Heritage Program\Data Management\ACCESS databases\ListMaster\ListMaster1_be.accdb"


conn = pyodbc.connect(r'Driver={Microsoft Access Driver (*.mdb, *.accdb)};DBQ='+accessdb+r';')
cursor_id = conn.cursor()
cursor_id.execute('SELECT * FROM idtable_find WHERE refcode IN ({})'.format(','.join('?'*len(refcodes))), refcodes)

id_df = pd.DataFrame((tuple(t) for t in cursor_id.fetchall()))
id_df = id_df.rename(columns={0:"ID",1:"site_name",2:"date",3:"refcode",4:"user"})
ids = id_df["ID"].tolist()
ids = [int(x) for x in ids]

species_list = conn.cursor()
species_list.execute('SELECT * FROM species_list WHERE ID IN ({})'.format(','.join('?'*len(ids))),ids)
sp_df = pd.DataFrame((tuple(t) for t in species_list.fetchall()))
sp_df = sp_df.rename(columns={0:"SPECIES_ID",1:"ID",2:"elem_name",3:"elem_found",4:"conf",5:"strata",6:"species_cover",7:"specimen_repo",8:"comm"})

m = sp_df.merge(id_df,how="left",on="ID")
final = m[["elem_name","elem_found","conf","conf","strata","species_cover","specimen_repo","comm","refcode"]]

#n = final.to_numpy()
#arcpy.da.NumPyArrayToTable(n,os.path.join("C:\\Users\\mmoore\\Documents\\ArcGIS\\Default.gdb","_TESTING"))
