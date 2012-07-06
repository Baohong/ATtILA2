'''
Test to evaluate consistency of LandCoverProportion Calculation

Created July 2012

@author: thultgren Torrin Hultgren, hultgren.torrin@epa.gov
'''

import arcpy
import ATtILA2
import parameters as p
import outputValidation

def runTest():
    try:
        if arcpy.Exists(p.outTable):
            arcpy.Delete_management(p.outTable)
            
        print "Running LandCoverProportion calculation"
        ATtILA2.metric.runLandCoverProportions(p.inReportingUnitFeature, p.reportingUnitIdField, p.inLandCoverGrid, 
                                               p._lccName, p.lccFilePath, p.metricsToRun, p.outTable, p.processingCellSize, 
                                               p.snapRaster, p.optionalFieldGroups)
    
        print "Testing LandCoverProportion results"
        results = outputValidation.compare(p.refLandCoverOutput,p.outTable)
        
        print results
    
    except Exception, e:
        ATtILA2.errors.standardErrorHandling(e)
        
if __name__ == '__main__':
    runTest()