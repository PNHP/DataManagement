#-------------------------------------------------------------------------------
# Name:        Find_duplicate_files
# Purpose:     Identifies duplicate files in folder tree by assigning unique MD5
#              hash to all files.  Deletes all duplicate files from secondary
#              folders (dupdirectories) and keeps all files in master directory.
# Author:      Molly Moore
# Created:     08/10/2016
# Updated:
#
# To Do List/Future ideas:
#
#-------------------------------------------------------------------------------

import os, hashlib, sys

# creates dictionary with hash as key and duplicate files as associated list
def deleteDups(maindirectory, pnhpdirectory, dupdirectories):
    hashmap = {}
    for path, dirs, files in os.walk(maindirectory):
        for name in files:
            fullname = os.path.join(path, name)
            try:
                with open(fullname, 'rb') as f:
                    d = f.read()
                    h = hashlib.md5(d).hexdigest()
                    filelist = hashmap.setdefault(h, [])
                    filelist.append(fullname)
            except IOError:
                pass

    # delete records in dictionary that have only 1 item (meaning no duplicate)
    for k, v in hashmap.items():
        if len(v) == 1:
            del hashmap[k]

    master_folder = []
    for k, v in hashmap.items():
        for string in v:
            if pnhpdirectory in string:
                master_folder.append(hashmap[k])

    # make dictionary into flat list
    try:
        dups = reduce(lambda x, y: x+y, master_folder)
        paths = [] # list of all files in duplicate directories
        for directory in dupdirectories:
            for root, dirs, files in os.walk(directory):
                for name in files:
                    paths.append(os.path.join(root, name))

        # if file in directory is also in duplicates list, it will be deleted
        DeletedFileSize = 0.00
        for file in paths:
            if file in dups:
                FileSize = os.path.getsize(file)
                DeletedFileSize = DeletedFileSize + FileSize
                print "Deleting file: " + file
                try:
                    os.remove(file)
                except WindowsError:
                    pass
            else:
                pass

        if DeletedFileSize == 0:
            print "No duplicate files found"
            print "Space saved: " + str(DeletedFileSize) + " gigabytes"
        else:
            DeletedFileSize = DeletedFileSize / 1073741824
            print "Space saved: " + str(DeletedFileSize) + " gigabytes"

    except TypeError:
        print "No duplicate files found."

maindirectory = "W:\\Heritage\Heritage_Data\\PNHP_Reference_Archive"
pnhpdirectory = "W:\\Heritage\Heritage_Data\\PNHP_Reference_Archive\\Master"
dupdirectories = ["W:\\Heritage\Heritage_Data\\PNHP_Reference_Archive\\_from_1st ref_transfer_HD",
"W:\\Heritage\Heritage_Data\\PNHP_Reference_Archive\\1_East_Refs_Jan2014"]

deleteDups(maindirectory, pnhpdirectory, dupdirectories)