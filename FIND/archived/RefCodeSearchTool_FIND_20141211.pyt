'''
Name:
Purpose:

Author:      K. Erath

Created:     11Sep2014
Updated:     11Dec2014

Updates:
11Dec2014
-Ignore feature services when determining location of local copy
05Nov2014
-Added option to create subset survey feature class
28Oct2014
-Removed datetime extra import
23Sep2014
-RefCodeSearch Tool accesses species list table in geodatabase rather than table view in the table of contents
-RefCodeSearch Tool can take string of snames and use either the AND or OR Boolean operators to get a list of reference codes associated with all or any of those species
'''


# import modules
import arcpy, time, datetime
import json, urllib, httplib, urllib2

# Set tools to overwrite existing outputs
arcpy.env.overwriteOutput = True

# Define global functions and variables to be used throughout toolbox

def parameter(displayName, name, datatype='GPFeatureLayer', defaultValue=None,
    parameterType='Required', direction='Input', multiValue=False):
    '''This function defines the parameter definitions for a tool. Using this
    function saves lines of code by prepopulating some of the values and also
    allows setting a default value.
    '''
    # create parameter with a few default properties
    param = arcpy.Parameter(
        displayName = displayName,
        name = name,
        datatype = datatype,
        parameterType = parameterType,
        direction = direction,
        multiValue = multiValue)

    # set new parameter to a default value
    param.value = defaultValue

    # return complete parameter object
    return param


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "FIND"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [RefCodeSearch]


class RefCodeSearch(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Reference Code Search Tool"
        self.description = '''Searches for reference codes based on species name.

        This tool takes a list of snames and gets a list of reference codes for
        each sname. The snames are placed into a Python list. Lists are iterable,
        so the code that creates the list of reference codes is written once, and
        it runs each time the script iterates over a new item in the sname list.

        To store the list of reference codes for each sname, a list of lists is
        created. It is actually a list of sets. Lists and sets are both built-in
        Python types and they both contain lists of values. They are both classes
        (classes can have properties and methods) and have different methods
        (they behave differently). Sets are handy because they remove duplicates
        from lists. In this case I used sets because later in the code I use an
        intersection which is a method of the set class not the list class. Another
        data type used in the script is a tuple. Tuples also contain lists of
        values but they are enclosed in parenthesis as opposed to brackets like
        lists. So when you are inserting a list of values into a string for the
        purpose of creating an SQL statement, it is nice to use tuples.

        If the AND Boolean operator is chosen, I get the intersection of all the
        lists of elcodes. The intersection is anything that is the same in all of
        the lists.

        If the OR Boolean operator is chosen, I put all the elcodes into 1 list
        and remove duplicates.

'''
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions using parameter function, defined at top of toolbox."""
        # parameter(displayName, name, datatype='GPFeatureLayer', defaultValue=None, parameterType='Required', direction='Input', multiValue=False)
        params = [
        parameter('Scientific Name(s)', 'sname', 'GPString'),
        parameter('Boolean Operator, necessary if multiple species are listed', 'bool_operator', datatype='GPString', defaultValue=None, parameterType='Optional', direction='Input', multiValue=False),
        parameter('Survey Site Output Feature Class', 'out_fc', datatype='DEFeatureClass', parameterType='Optional', direction='Derived'),
        parameter('FIND username', 'username', datatype='GPString', parameterType='Optional'),
        parameter('FIND password', 'password', datatype='GPString', parameterType='Optional')]
        # Set default value here:
        params[0].value = 'Cornus amomum'
        params[1].value = 'OR'
        # Create drop down menu for Boolean Operator parameter
        params[1].filter.list = ['OR', 'AND']
        # Disable username and password unless there is a value for survey site output feature class

        return params

    def execute(self, parameters, messages):
        """The source code of the tool."""
        # Define tool variables
        sname = parameters[0].valueAsText
        bool_operator = parameters[1].valueAsText
        out_fc = parameters[2].valueAsText
        username = parameters[3].valueAsText
        password = parameters[4].valueAsText

        # Convert sname to a Python list so we can iterate through snames
        snames1 = sname.split(',')
        # Remove any whitespace on leading or trailing end of each sname (so it doesn't matter if users put a space in between commas and snames)
        snames = [i.strip() for i in snames1]

        # Create map document object
        mxd = arcpy.mapping.MapDocument("CURRENT")
        # Create data frame object by listing all the data frames and getting the data frame at index zero
        # I'm making the assumption they will only have 1 data frame, or FIND will be in the first data frame
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        #--- Get workspace path for local copy of FIND from 'Survey Site' layer
        # Get a list of layer objects in the table of contents that are named "Survey Site"
        lyrlst = arcpy.mapping.ListLayers(mxd,"Survey Site",df)
        # Loop through each layer object in the list
        for lyr in lyrlst:
            # Objects can have properties and methods
            # Layer objects have several different types of properties, you can read about them here- http://resources.arcgis.com/en/help/main/10.2/index.html#//00s300000008000000
            # Here we will access the "workspacePath" property of the layer object

            # Not all layer objects support the same properties and methods,
            # so it is good practice to check and make sure this layer object supports that property before trying to access it
            if lyr.supports("workspacePath"):
                # Ignore any layers that are part of a feature service
                if lyr.workspacePath.startswith("https:"):
                    pass
                # If the layer supports workspacePath and the layer is not a feature service, get the workspace path of the local copy
                else:
                    # Store the pathname in a variable called workspace
                    workspace = lyr.workspacePath
                    # Print the pathname of the local copy to the progress dialogue box (\n means start new line)
                    arcpy.AddMessage("\nLocal Copy for {0} is {1}\n".format(lyr, workspace))
            else:
                arcpy.AddMessage("\nCould not determine location of local copy for {}\n".format(lyr))

        # Get dictionary of coded values and descriptions from list of domains
        domains = arcpy.da.ListDomains(workspace)
        for domain in domains:
            if domain.name == "ET":
                domain_dict = domain.codedValues
        # In a dictionary, keys are used to look up values
        # In the domain dict, elsubids are the keys and snames are the values
        # The dictionary must be inverted, so sname can be used to look up elsubid
        inverted_dict = dict([[v,k] for k,v in domain_dict.items()])

        # Create variable for species list table
        spec_tbl = r"{0}\SpeciesList".format(workspace)

        #--- Loop through each sname in the list of snames
        # List to store sets of refcodes
        # You can read more about sets here - https://docs.python.org/2/library/sets.html
        # To over simplify, a set is a list of unique values
        # We need the data type to be a set in order for the 'intersection' to work later in the code
        refcode_sets = []
        for sname in snames:
            # Use sname to look up elsubid
            elsubid = inverted_dict[sname]
            # Print elsubid to the progress dialogue box
            arcpy.AddMessage("\nElement Subnational ID: {}".format(elsubid))

            # Use elsubid to look up reference codes in the species list table
            # Create search cursor object
            srows = arcpy.da.SearchCursor(spec_tbl, "refcode", "elem_name = '{}'".format(elsubid))
            # Empty list to store reference codes
            refcode_list = []
            # For each row in the species list table where elem_name = elsubid (i.e. For each row in the search cursor)
            for srow in srows:
                # If reference code is not null
                if srow[0] != None:
                    # Convert reference code from unicode datatype to a regular string
                    refcode = str(srow[0]).lstrip('u')
                    # Append to list of reference codes
                    refcode_list.append(refcode)
                # If the reference code is null, skip it
                else:
                    pass
            # Print sname and associated reference codes to the progress dialogue box
            arcpy.AddMessage("{0}: {1}".format(sname, refcode_list))
            # Convert 'list' of refcodes to a 'set' and append to the refcode_sets list
            refcode_sets.append(set(refcode_list))

        # Check length of refcode sets (should be same as length of snames)
        # If there is only 1
        if len(refcode_sets) == 1:
            # Get first item in the refcode list and convert ot tuple (a tuple is enclosed in parenthesis instead of brackets like a list, so when we insert it into a string it works in a SQL query)
            refcodes = tuple(refcode_sets[0])
        # If there is more than 1
        else:
            # If the Boolean operator is AND
            if bool_operator == 'AND':
                # Get the intersection of all the sets and convert to tuple
                refcodes = tuple(set.intersection(*refcode_sets))
            # If the Boolean operator is not AND
            else:
                # Convert list of sets to a single list
                final_list = []
                # For set in refcode_list
                for s in refcode_sets:
                    # For item in set
                    for i in s:
                        # Append item to final list
                        final_list.append(i)
                # Remove duplicates and convert to tuple
                refcodes = tuple(set(final_list))

        # Check length of reference code list and create query
        if len(refcodes) == 0:
            arcpy.AddWarning("\nThere are no refcodes associated with this species.") # I added this line because it looks like some refcodes are null
            arcpy.AddWarning("Check to make sure there are no selections on the species table.")
        elif len(refcodes) > 1:
            query = "\nrefcode in {}\n".format(refcodes)
            arcpy.AddWarning(query)
        else:
            query = "\nrefcode = {}\n".format(refcodes[0])
            arcpy.AddWarning(query)

        # If the optional output feature class was filled in
        if out_fc:
            arcpy.AddMessage("Creating Survey Site subset feature class")
            servername = "maps.waterlandlife.org"

            def getToken(username, password, serverName, serverPort):
                tokenURL = "https://maps.waterlandlife.org/arcgis/tokens/"

                params = urllib.urlencode({'username': username, 'password': password,'client': 'requestip', 'f': 'json'})

                headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}

                # Connect to URL and post parameters
                httpConn = httplib.HTTPSConnection(serverName, serverPort)
                httpConn.request("POST", tokenURL, params, headers)

                # Read response
                response = httpConn.getresponse()
                print response.status
                if (response.status != 200):
                    httpConn.close()
                    print "Error while fetching tokens from admin URL. Please check the URL and try again."
                    return
                else:
                    data = response.read()
                    httpConn.close()

                    # Check that data returned is not an error object
                    if not assertJsonSuccess(data):
                        return

                    # Extract the token from it
                    token = json.loads(data)
                    return token['token']

            # A function that checks that the input JSON object is not an error object.
            def assertJsonSuccess(data):
                obj = json.loads(data)
                if 'status' in obj and obj['status'] == "error":
                    print "Error: JSON object returns an error. " + str(obj)
                    return False
                else:
                    return True

            # Query for service, with URL, where clause, fields and token
            baseURL= "https://maps.waterlandlife.org/arcgis/rest/services/PNHP_FIND/FeatureServer/0/query"
            where = query
            fields ='*'

            token = getToken(username, password, servername, None)
            query = "?where={}&outFields={}&returnGeometry=true&f=json&token={}".format(where, fields, token)
            fsURL = baseURL + query
            fs = arcpy.FeatureSet()
            fs.load(fsURL)

            arcpy.CopyFeatures_management(fs, out_fc)

        return
