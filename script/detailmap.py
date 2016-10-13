# Import the required modules
#
import arcpy, sys, traceback
from operator import itemgetter

##### Set up constants
topLevelDir = r"\\svrwp-file3\users\taoli\Projects\GateBook"
waterWorkspace = topLevelDir + r"\WaterNetwork.gdb"
cartoWorkspace = topLevelDir + r"\WaterCarto.gdb"
mxdPath = topLevelDir + r"\InsetMap.mxd"
pdfPath = topLevelDir + "\\PDF\\"
scriptPath = topLevelDir + "\\script\\"
toolPath = topLevelDir + "\\tools\\"
## Set up environment
arcpy.env.workspace = cartoWorkspace
arcpy.env.overwriteOutput = True
insetFeatureclass = cartoWorkspace + r"\HydGateValves_AggregatePolyFirst"
insetFieldlist = ["OID@", "Page_Name", "Inset_Num", "SHAPE@"]
insetPosDict = {"lbl_InsetPageName":(15.5, 10.35), "lbl_InsetNum1":(3.75, 7.25), "lbl_InsetNum2":(10.5, 7.25),
                "lbl_InsetNum3":(3.75, 2.5), "lbl_InsetNum4":(10.5, 2.5), "map_InsetFrame1":(4.25, 5.5),
                "map_InsetFrame2":(11, 5.5), "map_InsetFrame3":(4.25, 0.5), "map_InsetFrame4":(11, 0.5)}
insetDict = {}
mxd = arcpy.mapping.MapDocument(mxdPath)
arcpy.ImportToolbox(toolPath + r"\DetailViewTools.tbx")
# Toolname _ Toolbox Alias
arcpy.DetailViewModel_DetailViewTools()
for row in arcpy.da.SearchCursor(insetFeatureclass, insetFieldlist):
    try: 
        insetDict[row[1]].append([row[index] for index in range(len(insetFieldlist))])
    except KeyError:
        insetDict[row[1]] = []
        insetDict[row[1]].append([row[index] for index in range(len(insetFieldlist))])
# for each district grid sort the inset according to Inset_Num.
for dictkey in insetDict:
    #sort modifies the list in place.
    insetDict[dictkey].sort(key=itemgetter(2))
# build dict of textElement lables and dataframes
textElmDict = {}
for elm in arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT"):
    textElmDict[elm.name] = elm
dataFrameDict = {}
for elm in arcpy.mapping.ListDataFrames(mxd):
    dataFrameDict[elm.name] = elm
# Recursive function to print pages of insets
def createInsetMap(pageName, pdfDoc, pageList = None, insetPageCount = 0):
    #short this out if key is not in insetDict, ie no inset required
    if pageName not in insetDict.keys():
        return
    if not pageList:
        pageList = insetDict[pageName]
    # handles more than 4 inset
    if len(pageList) > 4:
        insetPageCount += 1
        finPageName = "Inset Map " + pageName + "_" + str(insetPageCount)
        textElmDict["lbl_InsetPageName"].text = finPageName
        privList = pageList[:4]
        for counter in range(len(privList)):
            textElmDict[("lbl_InsetNum" + str(counter+1))].elementPositionX = insetPosDict[("lbl_InsetNum" + str(counter+1))][0]
            textElmDict[("lbl_InsetNum" + str(counter+1))].elementPositionY = insetPosDict[("lbl_InsetNum" + str(counter+1))][1]
            dataFrameDict[("map_InsetFrame" + str(counter+1))].elementPositionX = insetPosDict[("map_InsetFrame" + str(counter+1))][0]
            dataFrameDict[("map_InsetFrame" + str(counter+1))].elementPositionY = insetPosDict[("map_InsetFrame" + str(counter+1))][1]
            dataFrameDict[("map_InsetFrame" + str(counter+1))].extent = pageList[counter][-1].extent
            dataFrameDict[("map_InsetFrame" + str(counter+1))].scale = dataFrameDict[("map_InsetFrame" + str(counter+1))].scale * 1.2
        pageList = pageList[4:]
        arcpy.mapping.ExportToPDF(mxd, pdfPath + "temp.pdf")
        pdfDoc.appendPages(pdfPath + "temp.pdf")
        createInsetMap(pageName, pdfDoc, pageList, insetPageCount)
    # handles inset 1 to 4 
    else:
        insetPageCount += 1
        finPageName = "Inset Map " + pageName + "_" + str(insetPageCount)
        textElmDict["lbl_InsetPageName"].text = finPageName
        for counter in range(len(pageList)):
            textElmDict[("lbl_InsetNum" + str(counter+1))].elementPositionX = insetPosDict[("lbl_InsetNum" + str(counter+1))][0]
            textElmDict[("lbl_InsetNum" + str(counter+1))].elementPositionY = insetPosDict[("lbl_InsetNum" + str(counter+1))][1]
            dataFrameDict[("map_InsetFrame" + str(counter+1))].elementPositionX = insetPosDict[("map_InsetFrame" + str(counter+1))][0]
            dataFrameDict[("map_InsetFrame" + str(counter+1))].elementPositionY = insetPosDict[("map_InsetFrame" + str(counter+1))][1]
            dataFrameDict[("map_InsetFrame" + str(counter+1))].extent = pageList[counter][-1].extent
            dataFrameDict[("map_InsetFrame" + str(counter+1))].scale = dataFrameDict[("map_InsetFrame" + str(counter+1))].scale * 1.2
        # move unused inset out of the page and set extent to blank area
        for counter in range(len(pageList),4):
            textElmDict[("lbl_InsetNum" + str(counter+1))].elementPositionX = insetPosDict[("lbl_InsetNum" + str(counter+1))][0] - 20
            textElmDict[("lbl_InsetNum" + str(counter+1))].elementPositionY = insetPosDict[("lbl_InsetNum" + str(counter+1))][1] - 20
            dataFrameDict[("map_InsetFrame" + str(counter+1))].elementPositionX = insetPosDict[("map_InsetFrame" + str(counter+1))][0] - 20
            dataFrameDict[("map_InsetFrame" + str(counter+1))].elementPositionY = insetPosDict[("map_InsetFrame" + str(counter+1))][1] - 20
            dataFrameDict[("map_InsetFrame" + str(counter+1))].extent = arcpy.Extent(10, 10, 20, 20)
        #arcpy.mapping.ExportToPDF(mxd, (pdfPath + finPageName + ".pdf"))
        arcpy.mapping.ExportToPDF(mxd, pdfPath + "temp.pdf")
        pdfDoc.appendPages(pdfPath + "temp.pdf")
    return
try:
    for key in insetDict:
        print insetDict[key]
        #createInsetMap(key)
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
