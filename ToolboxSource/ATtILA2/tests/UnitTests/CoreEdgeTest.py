'''
Test to evaluate consistency of Riparian LandCover Proportions Calculation

Created July 2012

@author: thultgren Torrin Hultgren, hultgren.torrin@epa.gov
'''

import arcpy
import ATtILA2
import parameters_eid as p
import outputValidation
from arcpy import env
env.overwriteOutput = True

def runTest():
    try:
        if arcpy.Exists(p.outTable):
            arcpy.Delete_management(p.outTable)
            
        print "Running Core Edge calculation"
        ATtILA2.metric.runCoreAndEdgeAreaMetrics(p.inReportingUnitFeature, p.reportingUnitIdField,p.inLandCoverGrid, p._lccName, p.lccFilePath, 
                                                 p.metricsToRun, p.inEdgeWidth, p.outTable, 
                                                 p.processingCellSize, p.snapRaster, p.optionalFieldGroups)
    
#        print "Testing RiparianLandCoverProportions results"
#        results = outputValidation.compare(p.refRiparianLandCover,p.outTable)
#        
#        print results
    
    except Exception, e: 
        ATtILA2.errors.standardErrorHandling(e)

def runTableTest():
    import os
    from ATtILA2 import setupAndRestore
    from ATtILA2 import utils
    from ATtILA2.constants import metricConstants
    from pylet import lcc
    try:
        if arcpy.Exists(p.outTable):
            arcpy.Delete_management(p.outTable)
        print "Running Table Test calculation"
        metricsBaseNameList, optionalGroupsList = setupAndRestore.standardSetup(p.snapRaster, p.processingCellSize,
                                                                                 os.path.dirname(p.outTable),
                                                                                 [p.metricsToRun,p.optionalFieldGroups] )
        lccObj = lcc.LandCoverClassification(p.lccFilePath)
        metricConst = metricConstants.caeamConstants()
        outIdField = utils.settings.getIdOutField(p.inReportingUnitFeature, p.reportingUnitIdField)
        for m in metricsBaseNameList:
            Core = m + "_Core"
            Edge = m + "_Edge"
            optionalGroupsList.append(Core)
            optionalGroupsList.append(Edge)
        newtable, metricsFieldnameDict = utils.table.tableWriterByClass(p.outTable, metricsBaseNameList,optionalGroupsList,
                                                                        metricConst, lccObj, outIdField)
        print metricsFieldnameDict  
             
    except Exception, e:
        ATtILA2.errors.standardErrorHandling(e)
        
if __name__ == '__main__':
    runTest()