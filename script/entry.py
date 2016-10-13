# GATE BOOK automation by Tao Li 
##### THE MXD need to be authorized from scratch WITH ArcFM Software Product set to NONE in ArcFM
##### Desktop Administrator.  Otherwise arcpy.mapping.exporttoX will NOT work, throws login prompt for data connection.  
# Import the required modules
#
import arcpy, sys, traceback, json, datetime, os, detailmap
from types import NoneType
from collections import namedtuple

##### Set up constants
topLevelDir = r"\\svrwp-file3\users\taoli\Projects\GateBook"
arcpy.env.workspace = topLevelDir + r"\WaterNetwork.gdb"
mxdPath = topLevelDir + r"\GateBOOKv5.mxd"
pdfPath = topLevelDir + "\\PDF\\"
scriptPath = topLevelDir + "\\script\\"

tblVertOffsetTuple = (
    ("NewLine"           , 0),
    ("NO."               , 0.4),
    ("SIZE"              , 0.6),
    ("KIND"              , 1),
    ("DATE INSTLD"       , 1),
    ("TURNS"             , 1),
    ("FT OF PL|CURB  A"  , 1.5),
    ("STREET  A"         , 2),
    ("FT OF PL|CURB  B"  , 1.5),
    ("STREET  B"         , 2),
    ("PWP COMMENTS"      , 5)
    )

##### helper functions
def formatfield(inputObj):
    if isinstance(inputObj, NoneType):
        outputObj = "-"
    elif isinstance(inputObj, unicode):
        outputObj = inputObj.encode("ascii", "ignore")
        # import datetime from datetime was not passing type checking...
    elif isinstance(inputObj, datetime.datetime):
        outputObj = datetime.datetime.strftime(inputObj, "%m/%d/%Y")
    else:
        outputObj = inputObj
    return outputObj

##### oject hook for json.load 
def _decode_list(data):
    rv = []
    for item in data:
        if isinstance(item, unicode):
            item = item.encode('utf-8')
        elif isinstance(item, list):
            item = _decode_list(item)
        elif isinstance(item, dict):
            item = _decode_dict(item)
        rv.append(item)
    return rv

def _decode_dict(data):
    rv = {}
    for key, value in data.iteritems():
        if isinstance(key, unicode):
            key = key.encode('utf-8')
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        elif isinstance(value, list):
            value = _decode_list(value)
        elif isinstance(value, dict):
            value = _decode_dict(value)
        rv[key] = value
    return rv

#this function is needed so that when people use letter instead of number for gate valve naming we don't break our script
def getRank(item):
    try:
        return int(item)
    except ValueError:
        return sum([ord(letter) for letter in item])+ 5000

# print layerDict["GateValve"].dataSource
def getVlvdict(pageName, layerDataSource, queryString):
    fieldList = ["OBJECTID", "FACILITYID", "DIAMETER", "MANUFACTURER", "INSTALLDATE", "TURNSTOOPEN", "DIRECTIONTOOPEN",
                 "LOC_OFFSET1", "LOC_DIRECTION1", "LOC_STREETNAME1", "LOC_STREETTYPE1",
                 "LOC_OFFSET2", "LOC_DIRECTION2", "LOC_STREETNAME2", "LOC_STREETTYPE2", "PWP_COMMENTS"]
    VlvnamedTuple = namedtuple("VlvnamedTuple", fieldList)
    Vlvdict = {}
    queryString = queryString + " AND FACILITYID LIKE '%-%' AND DISTRICTMAP = '" + pageName + "'"
    ##### Note Data Access curosr does NOT return row object, it just return a tuple. 
    with arcpy.da.SearchCursor(layerDataSource, fieldList, where_clause =  queryString) as cursor:
        rowNum = 1
        #ord fn is used to sort the 
        for row in sorted(cursor, key=lambda row: getRank((row[1].split("-")[-1]))):
            row = [formatfield(rowMember) for rowMember in row]
            VlvvalueRow = VlvnamedTuple(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10],
                                      row[11], row[12], row[13], row[14], row[15])
            Vlvdict[rowNum] = VlvvalueRow 
            rowNum += 1
    return Vlvdict

##### LIST map element by name and get XY position
def getElePosdict(mxd):
    ElePosdict = {}
    elementList = arcpy.mapping.ListLayoutElements(mxd)
    for ele in elementList:
        ElePosdict[ele.name] = (ele.elementPositionX, ele.elementPositionY)
    return ElePosdict

def moveMapGraphics(mxd, xoffset, yoffset):
    elementList = arcpy.mapping.ListLayoutElements(mxd)
    for ele in elementList:
        if ele.name[0:3] == "map":
            ele.elementPositionX += xoffset
            ele.elementPositionY += yoffset
            #print ele.name, ele.elementPositionX, ele.elementPositionY
    return None

def makeTable(mxd, rowcount, xinit, xoffsetlist, yinit, yoffset):
    # draw lines
    horzLine = arcpy.mapping.ListLayoutElements(mxd, "GRAPHIC_ELEMENT", "tblHorzLine")[0]
    vertLine = arcpy.mapping.ListLayoutElements(mxd, "GRAPHIC_ELEMENT", "tblVertLine")[0]
    for counter in range (rowcount + 1):
        temp_Horz = horzLine.clone("_clone")
        temp_Horz.elementPositionY = yinit - yoffset * counter
    for counter in range (rowcount):
        xtotaloffset = 0 
        for xoffset in xoffsetlist:
            temp_Vert = vertLine.clone("_clone")
            temp_Vert.elementPositionY = yinit - yoffset * counter
            xtotaloffset = xtotaloffset + xoffset[1]
            temp_Vert.elementPositionX = xinit + xtotaloffset
    # write column header
    textNode = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT", "tblTextNode")[0]
    xtotaloffset = 0 
    for xoffset in xoffsetlist[1:]:
        temp_textNode = textNode.clone("_clone")
        temp_textNode.text = xoffset[0]
        temp_textNode.elementPositionY = yinit - 0.03
        temp_textNode.elementPositionX = xinit + xtotaloffset + 0.03
        xtotaloffset = xtotaloffset + xoffset[1]
    return None 

# delete cloned element 
def delClonedEle(mxd):
    for elm in arcpy.mapping.ListLayoutElements(mxd, wildcard = "*_clone*"):
        elm.delete()
    return None

# rename map title
def changeMapTitle(mxd, titlestr):
    mapTitle = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT", "mixMapTableTitle")[0]
    mapTitle.text = titlestr
    #changing text move the element around so we need to reanchor
    mapTitle.elementPositionX = 0.55
    mapTitle.elementPositionY = 10.25
    return None

# populate table
def populateTable(mxd, currentrow, valvetuple, xinit, xoffsetlist, yinit, yoffset):
    # lambda one liner for truncate long string
    truncstr = lambda x: (len(x)>55 and (x[:55] + "...") or x)
    # do any additional formatting here
    fieldNO = valvetuple.FACILITYID.split("-")[-1]
    fieldSIZE = str(valvetuple.DIAMETER)
    fieldKIND = valvetuple.MANUFACTURER
    fieldDATEINSTALD = valvetuple.INSTALLDATE
    fieldTURNS = ' '.join([str(valvetuple.TURNSTOOPEN), valvetuple.DIRECTIONTOOPEN]) 
    fieldFTOFPLCURBA = ' '.join([str(valvetuple.LOC_OFFSET1), valvetuple.LOC_DIRECTION1])
    fieldSTREETA = ' '.join([valvetuple.LOC_STREETNAME1, valvetuple.LOC_STREETTYPE1])
    fieldFTOFPLCURBB = ' '.join([str(valvetuple.LOC_OFFSET2), valvetuple.LOC_DIRECTION2])
    fieldSTREETB = ' '.join([valvetuple.LOC_STREETNAME2, valvetuple.LOC_STREETTYPE2])
    fieldPWPCOMMENTS = truncstr(valvetuple.PWP_COMMENTS)
    field_tuple = (fieldNO, fieldSIZE, fieldKIND, fieldDATEINSTALD, fieldTURNS, fieldFTOFPLCURBA, fieldSTREETA, fieldFTOFPLCURBB, fieldSTREETB, fieldPWPCOMMENTS)
    textNode = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT", "tblTextNode")[0]
    xtotaloffset = 0 
    for xoffset, field in  zip(xoffsetlist[1:], field_tuple):
        temp_textNode = textNode.clone("_clone")
        temp_textNode.text = field
        temp_textNode.elementPositionY = yinit - 0.03 - (yoffset * currentrow)
        temp_textNode.elementPositionX = xinit + xtotaloffset + 0.03
        xtotaloffset = xtotaloffset + xoffset[1]
        #print xoffset, field
    return None

# print table pdf 
def createTablePDF(mxd, ValveDict, tblVertOffsetTuple, pdfPath, pageType, pageName, titlestr, pdfDoc):
    xinit = 0.5
    yinit = 10.0
    ydrop = 0.2
    ##### implement paging of tables
    moveMapGraphics(mxd, 50, 50)
    changeMapTitle(mxd, titlestr)
    currentrow = 1
    index = 1
    tablenumber = 1
    maxrowperpage = 40
    while True:
        try:
            if currentrow <= maxrowperpage:
                valvetuple = ValveDict[index]
                populateTable(mxd, currentrow, valvetuple, xinit, tblVertOffsetTuple, yinit, ydrop)
                index += 1
                currentrow += 1
            else:
                # no need to + 1 for header row, notice currentrow already incremented by if statement before being sent here
                makeTable(mxd, currentrow, xinit, tblVertOffsetTuple, yinit, ydrop)
                # export what we have written out up to this point
                #arcpy.mapping.ExportToPDF(mxd, pdfPath + pageType + "_" + str(tablenumber) + "_" + pageName + ".pdf")
                arcpy.mapping.ExportToPDF(mxd, pdfPath + "temp.pdf")
                pdfDoc.appendPages(pdfPath + "temp.pdf")
                #delete content of table
                delClonedEle(mxd)
                # write row 41 as first row on a clean sheet
                currentrow = 1
                valvetuple = ValveDict[index]
                populateTable(mxd, currentrow, valvetuple, xinit, tblVertOffsetTuple, yinit, ydrop)
                # increment currentrow just like in if statement
                currentrow += 1
                index += 1
                tablenumber += 1
        except KeyError:
                # current row alrady incremeanted from before but there is no record so minus one... +1 is for header
                makeTable(mxd, (currentrow + 1 -1), xinit, tblVertOffsetTuple, yinit, ydrop)
                # export what we have written out up to this point
                #arcpy.mapping.ExportToPDF(mxd, pdfPath + pageType + "_" + str(tablenumber) + "_" + pageName + ".pdf")
                arcpy.mapping.ExportToPDF(mxd, pdfPath + "temp.pdf")
                pdfDoc.appendPages(pdfPath + "temp.pdf")
                delClonedEle(mxd)
                moveMapGraphics(mxd, -50, -50)
                changeMapTitle(mxd, "GATE BOOK")
                break
    return None

try:

    ##### Build Up layer dictionary one time, this check all dataframes
    layerOfInterest = ["HydrantValve", "GateValve", "HighlightSA"]
    layerDict = {}
    mxd = arcpy.mapping.MapDocument(mxdPath)
    df = arcpy.mapping.ListDataFrames(mxd)[0]
    for layer in arcpy.mapping.ListLayers(mxd):
        if layer.name in layerOfInterest:
            ##### encode to ascii and ignore non-ascii char
            layerDict[layer.name.encode('ascii', 'ignore')] = layer
    ###### loop over all pages and export PDF
    ###### make sure we are sorting the data driven page by page_name field so that ie 016a-j follow 016a-i
    for pageNum in range(1, mxd.dataDrivenPages.pageCount + 1):  
        mxd.dataDrivenPages.currentPageID = pageNum
        pageName = mxd.dataDrivenPages.pageRow.Page_Name
        queryString = "PAGE_NAME = '%s'" % pageName.strip()
        print queryString
        pageNameList = pageName.split("-")
        if pageName and (pageNum > 328):
            ## above line specify pages to render, if printing freezes, which happens, open the map mxd, find the debug page number  
            if pageNameList[1] == "i":
                singlePdfPath = pdfPath + pageNameList[0] + ".pdf"
                print "making gatebook:  " + pageNameList[0]
                if os.path.exists(singlePdfPath):
                    os.remove(singlePdfPath)
                pdfDoc = arcpy.mapping.PDFDocumentCreate(singlePdfPath)
                layerDict["HighlightSA"].definitionQuery = queryString
                arcpy.mapping.ExportToPDF(mxd, pdfPath + "temp.pdf")
                pdfDoc.appendPages(pdfPath + "temp.pdf")
                #print inset maps
                detailmap.createInsetMap(pageName, pdfDoc)
            elif pageNameList[1] == "j":
                layerDict["HighlightSA"].definitionQuery = queryString
                arcpy.mapping.ExportToPDF(mxd, pdfPath + "temp.pdf")
                pdfDoc.appendPages(pdfPath + "temp.pdf")
                #print inset maps
                detailmap.createInsetMap(pageName, pdfDoc)
                GateValveDict = getVlvdict(pageNameList[0], layerDict["GateValve"].dataSource, "FACILITYID_TYPE IN ('GV', 'GV018-29', 'GV312-25', 'GV312-27', 'GV515-12')")
                #print GateValveDict
                createTablePDF(mxd, GateValveDict, tblVertOffsetTuple, pdfPath, "GVT", pageName, "GATE BOOK - Gate Valve Table", pdfDoc)
                HydValveDict = getVlvdict(pageNameList[0], layerDict["HydrantValve"].dataSource, "FUNCTION = 'HYD'")
                #print GateValveDict
                createTablePDF(mxd, HydValveDict, tblVertOffsetTuple, pdfPath, "HYD", pageName, "GATE BOOK - Hydrant Valve Table", pdfDoc)
                pdfDoc.saveAndClose()
                del pdfDoc
# clean up
    del mxd
    #--------------------------
except arcpy.ExecuteError: 
    # Get the tool error messages 
    # 
    msgs = arcpy.GetMessages(2) 

    # Return tool error messages for use with a script tool 
    #
    arcpy.AddError(msgs) 

    # Print tool error messages for use in Python/PythonWin 
    # 
    print msgs

except:
    # Get the traceback object
    #
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]

    # Concatenate information together concerning the error into a message string
    #
    pymsg = "PYTHON ERRORS:\nTraceback info:\n" + tbinfo + "\nError Info:\n" + str(sys.exc_info()[1])
    msgs = "ArcPy ERRORS:\n" + arcpy.GetMessages(2) + "\n"

    # Return python error messages for use in script tool or Python Window
    #
    arcpy.AddError(pymsg)
    arcpy.AddError(msgs)

    # Print Python error messages for use in Python / Python Window
    #
    print pymsg + "\n"
    print msgs
