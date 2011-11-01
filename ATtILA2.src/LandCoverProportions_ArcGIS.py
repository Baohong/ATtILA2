# LandCoverProportions_ArcGIS.py
# Michael A. Jackson, jackson.michael@epa.gov, majgis@gmail.com
# 2011-10-04
""" Land Cover Proportion Metrics

    DESCRIPTION
    
    ARGUMENTS
    
    REQUIREMENTS
    Spatial Analyst Extension

"""

import sys
import os
import arcpy
from collections import defaultdict
from esdlepy import lcc

# Check out any necessary licenses
arcpy.CheckOutExtension("spatial")

def main(argv):
    """ Start Here """    
    # Script arguments
    Input_reporting_unit_feature = arcpy.GetParameterAsText(0)
    Reporting_unit_ID_field = arcpy.GetParameterAsText(1)
    Input_land_cover_grid = arcpy.GetParameterAsText(2)
    lccFilePath = arcpy.GetParameterAsText(4)
    Metrics_to_run = arcpy.GetParameterAsText(5)
    Output_table = arcpy.GetParameterAsText(6)
    Processing_cell_size = arcpy.GetParameterAsText(7)
    Snap_raster = arcpy.GetParameterAsText(8)
    
    # XML file loaded into memory
    # lccFilePath is hard coded until it can be obtained from the tool dialog
    lccFilePath = r'L:\Priv\LEB\Projects\A-H\ATtILA2\src\ATtILA2.src\LandCoverClassifications\NLCD 2001.lcc'
    lccObj = lcc.LandCoverClassification(lccFilePath)

    # dummy dictionary
    classValuesDict = {}
    classValuesDict['for'] = (41, 42, 43)
    classValuesDict['wetl'] = (90, 91, 92, 93, 94, 95, 96, 97, 98, 99)
    classValuesDict['shrb'] = (51, 52)
    classValuesDict['ng'] = (71, 72, 73, 74)
    classValuesDict['agp'] = (81,)
    classValuesDict['agcr'] = (82,)
    classValuesDict['agcn'] = ()
    classValuesDict['nbar']=(31, 32)
    classValuesDict['ldr'] = (22,)
    classValuesDict['hdr'] = (23,)
    classValuesDict['coin'] = (24,)
    classValuesDict['agug'] = (21,)
    classValuesDict['water'] = (11, 12)
    
    
    # Constants
    
    # Set parameters for metric output field
    mPrefix = "p" # e.g. pFor, rAgt, sNat
    mField_type = "FLOAT" 
    mField_precision = 6
    mField_scale = 1
    
    # set value to be assign to output fields when the calculation is undefined
    nullValue = -1
    
    # set up containers for warnings if data anomalies are found
    
    emptyClasses = [] # selected metrics with empty value tuples in .lcc file
    extraValues = [] # grid values not contained/defined in .lcc file
    
    # the variables row and rows are initially set to None, so that they can
    # be deleted in the finally block regardless of where (or if) script fails
    out_row = None
    out_rows = None 
    
    TabArea_row = None
    TabArea_rows = None
    
    # get current snap environment to restore at end of script
    tempEnvironment0 = arcpy.env.snapRaster
        
    try:
        # Process: inputs        
        # create the specified output table - has to be a better way than this
        (out_path, out_name) = os.path.split(Output_table)
        # need to strip the dbf extension if the outpath is a geodatabase; 
        # should control this in the validate step or with an arcpy.ValidateTableName call
        if out_path.endswith("gdb"):
            if out_name.endswith("dbf"):
                out_name = out_name[0:-4]
        newTable = arcpy.CreateTable_management(out_path, out_name)
        
        # add standard fields to the output table
        # process the user input to add id field to output table
        orig_Fields = arcpy.ListFields(Input_reporting_unit_feature)
        for aFld in orig_Fields:
            if aFld.name == Reporting_unit_ID_field:
                id_name = aFld.name
                id_type = aFld.type
                id_precision = aFld.precision
                id_scale = aFld.scale
                break
            
        arcpy.AddField_management(newTable, id_name, id_type, id_precision, id_scale)
        arcpy.AddField_management(newTable, "LC_Overlap", "FLOAT", 6, 1)
    
        # add metric fields to the output table
        # parse the Metrics_to_run string into a list of selected metric base names
        metricsBaseList = []
        templist = Metrics_to_run.replace("'","").split(';')
        for alist in templist:
            metricsBaseList.append(alist.split('  ')[0])
        
        for mBase in metricsBaseList:
            arcpy.AddField_management(newTable, mPrefix+mBase, mField_type, mField_precision, mField_scale)
            
        # if a dbf table was specified as the output_table, a default field has already been
        # created in the newTable object. It needs to be deleted after other fields have been added.
        if out_name.endswith("dbf"):
            arcpy.DeleteField_management(newTable, "Field1") 
    
        # set the snap raster environment so the rasterized polygon theme aligns with land cover grid cell boundaries
        arcpy.env.snapRaster = Snap_raster
        
        # determine zone field for tabulate area 
        if id_type == "String":
            zone_field = id_name
        else:
            zone_field = "value"
        
        # rasterize the reporting unit theme. speeds up tabulate area process.
        scratch_Raster = arcpy.CreateScratchName("xxtmp", "", "RasterDataset")
        arcpy.PolygonToRaster_conversion(Input_reporting_unit_feature, Reporting_unit_ID_field, scratch_Raster, "CELL_CENTER", "NONE", Processing_cell_size)
        
        # use resultDict function to find the grid computed area of each input reporting unit
        resultDict = rasterVatToDict(scratch_Raster, zone_field)


        # Process: Tabulate Area
        # create name for a temporary table for the tabulate area geoprocess step
        # uses the current workspace - want to change to workspace specified in Output_table
        scratch_Table = arcpy.CreateScratchName("xtmp", "", "Dataset")
        arcpy.gp.TabulateArea_sa(scratch_Raster, zone_field, Input_land_cover_grid, "Value", scratch_Table, Processing_cell_size)
      
        
        
        # Process: outputs
        # get the fields from Tabulate Area table
        tabarea_flds = arcpy.ListFields(scratch_Table)
        
        # create the cursor to add data to the output table   
        out_rows = arcpy.InsertCursor(newTable)
        
        # create search cursor on TabAreaOut table
        TabArea_rows = arcpy.SearchCursor(scratch_Table)
        
        for TabArea_row in TabArea_rows:
            zoneIDvalue = TabArea_row.getValue(zone_field)
            
            out_row = out_rows.newRow()
            
            #Load row into dictionary or single variables
            tabAreaDict=defaultdict(lambda:0)
            
            # put the area figures for each grid value in a dictionary
            # and determine the total excluded and included value areas 
            # in the reporting unit
            excludedAreaSum = 0
            includedAreaSum = 0
            
            for aFld in tabarea_flds[2:]:
                valKey = aFld.name[6:]
                valArea = TabArea_row.getValue(aFld.name)
                tabAreaDict[valKey] = valArea

                # check if this grid value was defined in the lcc file
                if lccObj.values[valKey]:
                    # place the area for this grid value in the appropriate sum
                    if lccObj.values[valKey].excluded:
                        excludedAreaSum += valArea
                    else:
                        includedAreaSum += valArea
                
                else: # this grid value is not defined in the lcc file. set up a warning
                    includedAreaSum += valArea
                    if not valKey in extraValues:
                        extraValues.append(valKey)
            
            # sum the area values for each selected metric   
            for mBase in metricsBaseList:
                # get the values for this specified metric
                mBaseValueIDs = classValuesDict[mBase]
                # mBaseClass = lccObj.classes[mBase]
                # mBaseValueIDs = mBaseClass.valueIds
                                
                # if the metric value(s) definition tuple is empty
                if not mBaseValueIDs:
                    # put the metric name in the emptyClasses list for a warning message
                    if not mBase in emptyClasses:
                        emptyClasses.append(mBase)
                    
                    # assign the output field for this metric the null value    
                    out_row.setValue(mPrefix+mBase, nullValue)
                    # go to the next metric
                    continue
                    
                baseAreaSum = 0                         
                for aValueID in mBaseValueIDs:
                    aValueIDStr = str(aValueID)
                    baseAreaSum += tabAreaDict[aValueIDStr]
                
                if includedAreaSum > 0:
                    percentAreaBase = (baseAreaSum / includedAreaSum) * 100
                else: # all values found in reporting unit are in the excluded set
                    percentAreaBase = 0
                
                out_row.setValue(mPrefix+mBase, percentAreaBase)

            # set the reporting unit id value
            out_row.setValue(id_name, zoneIDvalue)
            
            # add lc_overlap calculation to row
            zoneArea = resultDict[zoneIDvalue][1]
            overlapCalc = ((includedAreaSum+excludedAreaSum)/zoneArea) * 100
            out_row.setValue('LC_Overlap', overlapCalc)
            
            # commit the row to the output table
            out_rows.insertRow(out_row)

        # Housekeeping
        # delete the scratch themes
        arcpy.Delete_management(scratch_Table)
        arcpy.Delete_management(scratch_Raster)

        # Add warnings if necessary
        if emptyClasses:
            warningString = "The following metric(s) were selected, but were undefined in lcc file: "
            for aItem in emptyClasses:
                warningString = warningString+aItem+" "
                
            arcpy.AddWarning(warningString+"- Assigned null value in output.")
            
        if extraValues:
            warningString = "The following grid value(s) were not defined in the lcc file: "
            for aItem in extraValues:
                warningString = warningString+aItem+" "
                
            arcpy.AddWarning(warningString+"- The area for these grid cells was still used in metric calculations.")
                
    except arcpy.ExecuteError:
        arcpy.AddError(arcpy.GetMessages(2))
        
    except:
        arcpy.AddError("Non-tool error occurred")
        
    finally:
        # delete cursor and row objects to remove locks on the data
        if out_row:
            del out_row
        if out_rows:
            del out_rows
        if TabArea_rows:
            del TabArea_rows
        if TabArea_row:
            del TabArea_row
            
        # restore the environments
        arcpy.env.snapRaster = tempEnvironment0
        
        # return the spatial analyst license    
        arcpy.CheckInExtension("spatial")


def rasterVatToDict(raster, key_field):
    """ Import raster VAT to dictionary """

    resultDict = {}
    
    desc = arcpy.Describe(raster)
    meanCellArea = desc.meanCellHeight * desc.meanCellWidth
    cur = arcpy.SearchCursor(raster)
    for row in cur:
        key = row.getValue(key_field)
        count = row.count
        area = count * meanCellArea
        resultDict[key] = (count, area)
    
    del row
    del cur

    return resultDict

if __name__ == "__main__":
    main(sys.argv)