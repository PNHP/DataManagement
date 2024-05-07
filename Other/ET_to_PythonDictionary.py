# -------------------------------------------------------------------------------
# Name:        ET_to_PythonDictionary.py
# Purpose:     Use this script to create a .py document of dictionaries with ET values in them for FIND. These dictionaries
#              can then be imported into other scripts that require the coded value domain.
# Author:      MMoore
# Created:     01/28/2020
# Updates:
# 03/25/2024 - updated to write to .py script so that we don't need to copy/paste dictionaries into .py script
# -------------------------------------------------------------------------------

et_year = 2024

# import packages
import pandas as pd
import json

# define folder and names of Excel files where the updated ETs are stored
et_folder = r'P:\Conservation Programs\Natural Heritage Program\Data Management\Instructions, procedures and documentation\FIND\DM Documentation\ET\20240316_'
et_comm = r'FIND_comm_ET_2024'
et_insect = r'ET_INSECT'
et_invert = r'ET_INVERT'
et_lep = r'ET_LEP'
et_plant = r'ET_PLANT'
et_vert = r'ET_VERT'
et_all = r'ET_updatedCommunities'

# create function to load excel spreadsheet into dictionary
def loadExcel(in_sheet):
    df = pd.read_excel(io=in_sheet, sheet_name="Sheet1")
    df = df[['ELEMENT_SUBNATIONAL_ID', 'SCIENTIFIC_NAME']]
    d = dict(zip(df.ELEMENT_SUBNATIONAL_ID, df.SCIENTIFIC_NAME))
    return d

# run functions for all et files
et_comm = loadExcel(et_folder + et_comm + ".xlsx")
et_insect = loadExcel(et_folder + et_insect + ".xlsx")
et_invert = loadExcel(et_folder + et_invert + ".xlsx")
et_lep = loadExcel(et_folder + et_lep + ".xlsx")
et_plant = loadExcel(et_folder + et_plant + ".xlsx")
et_vert = loadExcel(et_folder + et_vert + ".xlsx")
et_all = loadExcel(et_folder + et_all + ".xlsx")

# create lists for loops
dict_names = ["et_comm", "et_insect", "et_invert", "et_lep", "et_plant", "et_vert", "et_all"]
dicts = [et_comm, et_insect, et_invert, et_lep, et_plant, et_vert, et_all]

# write dictionaries to .py file
with open(r'H:\Scripts\DataManagement\FIND\FIND_et_'+str(et_year)+'.py', 'w') as convert_file:
    for n,d in zip(dict_names,dicts):
        convert_file.write(n + " = " + json.dumps(d) + "\n")
