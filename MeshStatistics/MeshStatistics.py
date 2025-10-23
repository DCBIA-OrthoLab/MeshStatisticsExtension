from __future__ import print_function

import numpy
import math
import re
import csv
import os
import sys
import logging
from __main__ import vtk, qt, ctk, slicer
from random import randint
from slicer.ScriptedLoadableModule import *

class MeshStatistics(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        parent.title = 'Mesh Statistics'
        parent.categories = ['Quantification']
        parent.dependencies = []
        parent.contributors = ['Lucie Macron']
        parent.helpText = """
            The goal of this module is to compute statistics on a model,
            considering a specific region (defined with Pick'n Paint) or on the entire shape.
            Statistics are: Minimum Value, Maximum Value, Average, Standard Deviation, and different type of percentile.
            It's possible to export those values as CSV file.
            Before working on Mesh Statistics, you have to compute ModelToModelDistance.
            """
        parent.acknowledgementText = """
            This file was originally developed by Lucie Macron, University of Michigan.
            """
        self.parent = parent


class MeshStatisticsWidget(ScriptedLoadableModuleWidget):
    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        print("-------Mesh Statistic Widget Setup-------")
        # -------------------------------------------------------------------------------------
        self.modelList = list()
        self.fieldList = list()
        self.ROIList = list()
        self.ROIDict = dict()  # Key = Name of ROI
                               # Value = Dictionary of Fields (key = Name of Field
                               #                               Value = dictionary of shapes
                               #                                             key = name of shapes
                               #                                             value = Statistics store()

        self.logic = MeshStatisticsLogic(self)

        # ---------------------------------------------------------------- #
        # ---------------- Definition of the UI interface ---------------- #
        # ---------------------------------------------------------------- #

        # ------------ Loading of the .ui file ---------- #

        modulePath = os.path.dirname(slicer.util.modulePath(self.moduleName))
        path = os.path.join(modulePath, 'Resources', 'UI', '%s.ui' % self.moduleName)

        self.layout = self.parent.layout()
        self.widget = slicer.util.loadUI(path)
        self.layout.addWidget(self.widget)

        # ------------------------------------------------------------------------------------
        #                                    SHAPES INPUT
        # ------------------------------------------------------------------------------------
        self.inputComboBox = self.logic.get("inputComboBox")
        self.inputComboBox.setMRMLScene(slicer.mrmlScene)
        self.inputComboBox.connect('checkedNodesChanged()', self.onInputComboBoxCheckedNodesChanged)
        # ------------------------------------------------------------------------------------
        #                                  ROI TABLE
        # ------------------------------------------------------------------------------------
        self.ROIComboBox = self.logic.get("ROIComboBox")
        self.ROICheckBox = self.logic.get("ROICheckBox")
        self.ROICheckBox.connect('stateChanged(int)', self.onROICheckBoxStateChanged)
        # ------------------------------------------------------------------------------------
        #                                  FIELD TABLE
        # ------------------------------------------------------------------------------------
        self.tableField = self.logic.get("tableField")
        self.tableField.setColumnCount(2)
        self.tableField.setMinimumHeight(250)
        self.tableField.setHorizontalHeaderLabels([' ', ' Field Name '])
        self.tableField.setColumnWidth(0, 20)
        self.tableField.setColumnWidth(1, 260)
        self.tableField.setSizePolicy(qt.QSizePolicy().Expanding, qt.QSizePolicy().Expanding)
        # ------------------------------------------------------------------------------------
        #                                    RUN
        # ------------------------------------------------------------------------------------
        self.runButton = self.logic.get("runButton")
        self.runButton.connect('clicked()', self.onRunButton)

        # ------------------------------------------------------------------------------------
        #                          Statistics Table - Export
        # ------------------------------------------------------------------------------------
        self.mainLayout = self.logic.get("mainLayout")
        self.tabROI = qt.QTabWidget()
        self.tabROI.setTabPosition(0)
        self.tabROI.adjustSize()
        # ---------------------------- Directory - Export Button -----------------------------
        self.directoryExport = ctk.ctkDirectoryButton()
        self.exportCheckBox = qt.QCheckBox('Separate Files')
        self.exportCheckBox.setChecked(True)
        self.exportButton = qt.QPushButton(' Export ')
        self.exportButton.enabled = True
        self.exportPointValueCheckBox = qt.QCheckBox('Export Value on Each Point')
        
        self.exportLayout = qt.QVBoxLayout()
        self.directoryAndExportLayout = qt.QHBoxLayout()
        self.directoryAndExportLayout.addWidget(self.directoryExport)
        self.directoryAndExportLayout.addWidget(self.exportCheckBox)
        self.directoryAndExportLayout.addWidget(self.exportPointValueCheckBox)
        self.exportButtonsLayout = qt.QHBoxLayout()
        self.exportButtonsLayout.addWidget(self.exportButton)
        

        self.exportLayout.addLayout(self.directoryAndExportLayout)
        self.exportLayout.addLayout(self.exportButtonsLayout)
        
        self.layout.addStretch(1)
        self.logic.updateInterface(self.tableField, self.ROIComboBox, self.ROIList, self.modelList, self.mainLayout)

        # ------------------------------------------------------------------------------------
        #                                   OBSERVERS
        # ------------------------------------------------------------------------------------

        slicer.mrmlScene.AddObserver(slicer.mrmlScene.EndCloseEvent, self.onCloseScene)

    def onCloseScene(self, obj, event):
        # initialize Parameters
        self.modelList = list()
        self.fieldList = list()
        self.ROIList = list()
        self.ROIDict = dict()
        self.ROIComboBox.clear()
        self.tableField.clearContents()
        self.tableField.setRowCount(0)
        self.tableField.setRowCount(1)
        self.tableField.setSpan(0,0,1,2)
        label = qt.QLabel(' Please select at least a model! ')
        label.setStyleSheet(' qproperty-alignment: AlignCenter; }')
        self.tableField.setCellWidget(0, 0, label)

    def onInputComboBoxCheckedNodesChanged(self):
        self.modelList = self.inputComboBox.checkedNodes()
        self.runButton.enabled = not self.inputComboBox.noneChecked()
        self.logic.updateInterface(self.tableField, self.ROIComboBox, self.ROIList, self.modelList, self.mainLayout)

    def onROICheckBoxStateChanged(self, intCheckState):
        # intCheckState == 2 when checked
        # intCheckState == 0 when unchecked
        if intCheckState == 2:
            self.ROIComboBox.setEnabled(False)
        else:
            if intCheckState == 0:
                self.ROIComboBox.setEnabled(True)

    def onRunButton(self):
        self.ROIDict.clear()
        if self.modelList:
            self.logic.removeTable(self.mainLayout, self.tabROI)
            self.exportButton.disconnect('clicked()', self.onExportButton)
            self.mainLayout.removeWidget(self.exportButton)
            self.mainLayout.removeItem(self.exportLayout)
        self.logic.displayStatistics(self.ROICheckBox.isChecked(), self.ROIList, self.ROIDict, self.ROIComboBox,
                                     self.tableField, self.modelList, self.tabROI, self.mainLayout)
        self.mainLayout.addLayout(self.exportLayout)
        self.exportButton.connect('clicked()', self.onExportButton)


    def onExportButton(self):
        self.logic.exportationFunction(self.directoryExport, self.exportCheckBox.isChecked(), self.ROIDict)
        if self.exportPointValueCheckBox.isChecked():
            self.logic.ExportationValueOnEachPoint(self.directoryExport, self.ROIDict)


class MeshStatisticsLogic(ScriptedLoadableModuleLogic):
    class StatisticStore(object):
        def __init__(self):
            self.min = 0
            self.max = 0
            self.mean = 0
            self.std = 0
            self.percentile5 = 0
            self.percentile15 = 0
            self.percentile25 = 0
            self.percentile50 = 0
            self.percentile75 = 0
            self.percentile85 = 0
            self.percentile95 = 0

    def __init__(self, interface=None):
        self.interface = interface
        self.numberOfDecimals = 3
        system = qt.QLocale().system()
        self.decimalPoint = chr(system.decimalPoint())

    # -------------------------------------------------------- #
    # ----------- Connection of the User Interface ----------- #
    # -------------------------------------------------------- #

    # This function will look for an object with the given name in the UI and return it.
    def get(self, objectName):
        return slicer.util.findChildren(widget=self.interface.widget, name=objectName)[0]

    def updateInterface(self, tableField, ROIComboBox, ROIList, modelList, layout):
        tableField.clearContents()
        tableField.setRowCount(0)
        
        ROIComboBox.clear()
        ROIComboBox.addItem('Entire Model')
        del ROIList[:]
        ROIList.append('Entire Model')
        tableFieldNumRows = 0
        expression = '_ROI'
        
        if tableField.rowCount == 0:
            tableField.setRowCount(1)
            tableField.setSpan(0,0,1,2)
            label = qt.QLabel(' Please select at least a model! ')
            label.setStyleSheet(' QLabel{ qproperty-alignment: AlignCenter; }')
            tableField.setCellWidget(tableFieldNumRows, 0, label)

        if modelList:
            tableField.setSpan(0,0,1,1)
            numberOfArrayList = list()
            for model in modelList:
                numberOfArrayList.append(model.GetPolyData().GetPointData().GetNumberOfArrays())
            # set the model with the higher number of fields as reference
            modelOfReference = modelList[numberOfArrayList.index(max(numberOfArrayList))]
            PointDataOfReference = modelOfReference.GetPolyData().GetPointData()
            numOfArrayOfReference = PointDataOfReference.GetNumberOfArrays()

            fieldInCommon = list()
            fieldNotInCommon = []
            fieldNameOfRefList = list()
            fieldModel = list()

            del fieldNameOfRefList[:]
            for i in range(0, numOfArrayOfReference):
                if PointDataOfReference.GetArray(i).GetNumberOfComponents() == 1:
                    fieldNameOfRefList.append(PointDataOfReference.GetArray(i).GetName())
                    fieldInCommon.append(PointDataOfReference.GetArray(i).GetName())

            if modelList.__len__() > 1:
                for model in modelList:
                    del fieldModel[:]
                    if model.GetID() != modelOfReference.GetID():
                        numOfArray = model.GetPolyData().GetPointData().GetNumberOfArrays()
                        for i in range(0, numOfArray):
                            if model.GetPolyData().GetPointData().GetArray(i).GetNumberOfComponents() == 1:
                                fieldModel.append(model.GetPolyData().GetPointData().GetArray(i).GetName())
                        fieldInCommon, tempFieldNotInCommon = self.compareList(fieldInCommon, fieldModel)
                        fieldNotInCommon = fieldNotInCommon + tempFieldNotInCommon

            for arrayName in set(fieldInCommon):
                if not re.search(expression, arrayName):
                    tableFieldNumRows += 1
                    tableField.setMinimumHeight(tableFieldNumRows*35)
                    tableField.setRowCount(tableFieldNumRows)
                    tableField.setCellWidget(tableFieldNumRows - 1, 0, qt.QCheckBox())
                    label = qt.QLabel(arrayName)
                    label.setStyleSheet(' QLabel{qproperty-alignment: AlignVCenter | AlignLeft; }')
                    tableField.setCellWidget(tableFieldNumRows - 1, 1, label)
                else:
                    ROIComboBox.addItem(arrayName)
                    ROIList.append(arrayName)

            for arrayName in set(fieldNotInCommon):
                if not re.search(expression, arrayName):
                    tableFieldNumRows += 1
                    tableField.setMinimumHeight(tableFieldNumRows*35)
                    tableField.setRowCount(tableFieldNumRows)
                    label = qt.QLabel(arrayName)
                    label.setStyleSheet(' QLabel{ font-style:oblique; text-decoration:line-through;  }')
                    tableField.setCellWidget(tableFieldNumRows - 1, 1, label )

        layout.addStretch(1)

    def compareList(self, list1, list2):
        ListInCommon = list(set(list1) & set(list2))
        ListNotInCommon = (list(set(list1) - set(list2)) + list(set(list2) - set(list1)))
        return ListInCommon, ListNotInCommon

    def defineStatisticsTable(self, fieldDictionaryValue):
        statTable = qt.QTableWidget()
        numberOfRows = fieldDictionaryValue.__len__()
        statTable.setRowCount(numberOfRows)
        i = numberOfRows - 1
        statTable.setMinimumHeight(0)  # fit to contents
        statTable.setMinimumWidth(55)

        statTable.setColumnCount(12)
        statTable.setHorizontalHeaderLabels(['Model','Min','Max','Mean','SD','Per5','Per15','Per25','Per50','Per75','Per85','Per95'])
        # Add Values:
        for key, value in fieldDictionaryValue.items():
            statTable.setCellWidget(i, 0, qt.QLabel(key))
            statTable.setCellWidget(i, 1, qt.QLabel(value.min))
            statTable.cellWidget(i,1).setStyleSheet(' QLabel{ qproperty-alignment: AlignCenter;}')
            statTable.setCellWidget(i, 2, qt.QLabel(value.max))
            statTable.cellWidget(i,2).setStyleSheet(' QLabel{ qproperty-alignment: AlignCenter;}')
            statTable.setCellWidget(i, 3, qt.QLabel(value.mean))
            statTable.cellWidget(i,3).setStyleSheet(' QLabel{ qproperty-alignment: AlignCenter;}')
            statTable.setCellWidget(i, 4, qt.QLabel(value.std))
            statTable.cellWidget(i,4).setStyleSheet(' QLabel{ qproperty-alignment: AlignCenter;}')
            statTable.setCellWidget(i, 5, qt.QLabel(value.percentile5))
            statTable.cellWidget(i,5).setStyleSheet(' QLabel{ qproperty-alignment: AlignCenter;}')
            statTable.setCellWidget(i, 6, qt.QLabel(value.percentile15))
            statTable.cellWidget(i,6).setStyleSheet(' QLabel{ qproperty-alignment: AlignCenter;}')
            statTable.setCellWidget(i, 7, qt.QLabel(value.percentile25))
            statTable.cellWidget(i,7).setStyleSheet(' QLabel{ qproperty-alignment: AlignCenter;}')
            statTable.setCellWidget(i, 8, qt.QLabel(value.percentile50))
            statTable.cellWidget(i,8).setStyleSheet(' QLabel{ qproperty-alignment: AlignCenter;}')
            statTable.setCellWidget(i, 9, qt.QLabel(value.percentile75))
            statTable.cellWidget(i,9).setStyleSheet(' QLabel{ qproperty-alignment: AlignCenter;}')
            statTable.setCellWidget(i, 10, qt.QLabel(value.percentile85))
            statTable.cellWidget(i,10).setStyleSheet(' QLabel{ qproperty-alignment: AlignCenter;}')
            statTable.setCellWidget(i, 11, qt.QLabel(value.percentile95))
            statTable.cellWidget(i,11).setStyleSheet(' QLabel{ qproperty-alignment: AlignCenter;}')
            i -= 1
        statTable.resizeColumnToContents(0)
        return statTable


    def updateTable(self, ROIDict, tabROI, layout):
        tabROI.setMinimumWidth(100*ROIDict.__len__())
        for ROIName, FieldDict in ROIDict.items():
            tab = qt.QTabWidget()
            tab.adjustSize()
            tab.setTabPosition(1)
            for fieldName, fieldDictValue in FieldDict.items():
                statisticsTable = self.defineStatisticsTable(fieldDictValue)
                tab.addTab(statisticsTable, fieldName)
            tabROI.addTab(tab, ROIName)
        layout.addWidget(tabROI)

    def displayStatistics(self, ROICheckBoxState, ROIList, ROIDict, ROIComboBox, tableField, modelList, tabROI, layout):
        if ROICheckBoxState:
            for ROIName in ROIList:
                if not ROIName in ROIDict:
                    ROIDict[ROIName] = dict()
        else:
            ROIToCompute = ROIComboBox.currentText
            if not ROIToCompute in ROIDict:
                ROIDict[ROIToCompute] = dict()
                
        numberOfRowField = tableField.rowCount
        for ROIName, ROIFieldDict in ROIDict.items():
            for i in range(0, numberOfRowField):
                widget = tableField.cellWidget(i, 0)
                if widget and widget.isChecked():
                    ROIFieldDict[tableField.cellWidget(i, 1).text] = dict()
            for fieldName, fieldValue in ROIFieldDict.items():
                for shape in modelList:
                    activePointData = shape.GetModelDisplayNode().GetInputPolyData().GetPointData()
                    fieldArray = activePointData.GetArray(fieldName)
                    fieldValue[shape.GetName()] = self.StatisticStore()
                    if ROIName == 'Entire Model':
                        self.computeAll(fieldArray, fieldValue[shape.GetName()], None)
                    else:
                        ROIArray = activePointData.GetArray(ROIName)
                        self.computeAll(fieldArray, fieldValue[shape.GetName()], ROIArray)
        self.updateTable(ROIDict, tabROI, layout)

    def removeTable(self, layout, tabROI):
        # Remove table if it already exists:
        indexWidgetTabROI = layout.indexOf(tabROI)
        if indexWidgetTabROI != -1:
            for i in range(0, tabROI.count):
                tabWidget = tabROI.widget(i)
                for i in range(0, tabWidget.count):
                    tableWidget = tabWidget.widget(i)
                    tableWidget.clearContents()
                    tableWidget.setRowCount(0)
                tabWidget.clear()
            tabROI.clear()

    def defineArray(self, fieldArray, ROIArray):
        #  Define array of value from fieldArray(array with all the distances from ModelToModelDistance)
        #  using ROIArray as a mask
        #  Return a numpy.array to be able to use numpy's method to compute statistics
        valueList = list()
        bool = True
        if ROIArray == None:
            for i in range(0, fieldArray.GetNumberOfTuples()):
                valueList.append(fieldArray.GetValue(i))
            valueArray = numpy.array(valueList)
        else:
            if ROIArray.GetNumberOfTuples() != fieldArray.GetNumberOfTuples():
                print('Size of ROIArray and fieldArray are not the same!!!')
                bool = False
            else:
                for i in range(0, fieldArray.GetNumberOfTuples()):
                    if ROIArray.GetValue(i) == 1.0:
                        valueList.append(fieldArray.GetValue(i))
                valueArray = numpy.array(valueList)
        return bool, valueArray

    def computeMean(self, valueArray):
        #  valueArray is an array in which values to compute statistics on are stored
        return round(numpy.mean(valueArray), self.numberOfDecimals)

    def computeMinMax(self, valueArray):
        #  valueArray is an array in which values to compute statistics on are stored
        return round(numpy.min(valueArray), self.numberOfDecimals), round(numpy.max(valueArray), self.numberOfDecimals)

    def computeStandardDeviation(self, valueArray):
        #  valueArray is an array in which values to compute statistics on are stored
        return round(numpy.std(valueArray), self.numberOfDecimals)

    def computeQuantiles(self, valueArray):
        quantiles = [0.05, 0.15, 0.25, 0.50, 0.75, 0.85, 0.95]
        quantile_values = numpy.quantile(valueArray, quantiles)
        quantile_values = numpy.around(quantile_values, self.numberOfDecimals)
        return quantile_values


    def computeAll(self, fieldArray, fieldState, ROIArray):
        bool, array = self.defineArray(fieldArray, ROIArray)
        if len(array) == 0:
            slicer.util.errorDisplay("The ROI is empty")
            return
        if bool:
            fieldState.min, fieldState.max = self.computeMinMax(array)
            fieldState.mean = self.computeMean(array)
            fieldState.std = self.computeStandardDeviation(array)

            quantile_values = self.computeQuantiles(array)

            fieldState.percentile5 = quantile_values[0]
            fieldState.percentile15 = quantile_values[1]
            fieldState.percentile25 = quantile_values[2]
            fieldState.percentile50 = quantile_values[3]
            fieldState.percentile75 = quantile_values[4]
            fieldState.percentile85 = quantile_values[5]
            fieldState.percentile95 = quantile_values[6]

    def writeFieldFile(self, fileWriter, modelDict):
        #  Function defined to export all statistics of a field concidering a file writer (fileWriter)
        #  and a dictionary of models (modelDict) where statistics are stored
        for shapeName, shapeStats in modelDict.items():
            fileWriter.writerow([shapeName,
                                 shapeStats.min,
                                 shapeStats.max,
                                 shapeStats.mean,
                                 shapeStats.std,
                                 shapeStats.percentile5,
                                 shapeStats.percentile15,
                                 shapeStats.percentile25,
                                 shapeStats.percentile50,
                                 shapeStats.percentile75,
                                 shapeStats.percentile85,
                                 shapeStats.percentile95])

    def exportAllAsCSV(self, filename, ROIName, ROIDictValue):
        #  Export all fields on the same csv file considering a region
        file = open(filename, 'w')
        cw = csv.writer(file, delimiter=',')
        cw.writerow([ROIName])
        cw.writerow([' '])
        for fieldName, shapeDict in sorted(ROIDictValue.items()):
            cw.writerow([fieldName])
            cw.writerow(['Model','Min','Max','Mean','SD','Per5','Per15','Per25','Per50','Per75','Per85','Per95'])
            self.writeFieldFile(cw, shapeDict)
            cw.writerow([' '])
        file.close()
        if self.decimalPoint != '.':
            self.replaceCharac(filename, ',', ';') # change the Delimiter and put a semicolon instead of a comma
            self.replaceCharac(filename, '.', self.decimalPoint) # change the decimal separator '.' for a comma

    def exportFieldAsCSV(self, filename, fieldName, shapeDict):
        #  Export fields on different csv files
        file = open(filename, 'w')
        cw = csv.writer(file, delimiter=',')
        cw.writerow([fieldName])
        cw.writerow(['Model','Min','Max','Mean','SD','Per5','Per15','Per25','Per50','Per75','Per85','Per95'])
        self.writeFieldFile(cw, shapeDict)
        file.close()
        if self.decimalPoint != '.':
            self.replaceCharac(filename, ',', ';') # change the Delimiter and put a semicolon instead of a comma
            self.replaceCharac(filename, '.', self.decimalPoint) # change the decimal separator '.' for a comma

    
    def exportPointValueAsCSV(self, filename, fieldArray, ROIArray):
        #Exportation of the value stored for each point:
        file = open(filename, 'w')
        cw = csv.writer(file, delimiter=',')
        bool, arrayToReturn = self.defineArray(fieldArray, ROIArray)
        if len(arrayToReturn) == 0:
            slicer.util.errorDisplay("The ROI is empty")
            return
        if bool:
            for value in arrayToReturn:
                cw.writerow([value])
            file.close()
            if self.decimalPoint != '.':
                self.replaceCharac(filename, ',', ';') # change the Delimiter and put a semicolon instead of a comma
                self.replaceCharac(filename, '.', self.decimalPoint) # change the decimal separator '.' for a comma


    def replaceCharac(self, filename, oldCharac, newCharac):
        #  Function to replace a charactere (oldCharac) in a file (filename) by a new one (newCharac)
        file = open(filename,'r')
        lines = file.readlines()
        with open(filename, 'r') as file:
            lines = [line.replace(oldCharac, newCharac) for line in file.readlines()]
        file.close()
        file = open(filename, 'w')
        file.writelines(lines)
        file.close()

    def exportationFunction(self, directoryExport, exportCheckBoxState, ROIDict):
        directory = directoryExport.directory
        messageBox = ctk.ctkMessageBox()
        messageBox.setWindowTitle('WARNING')
        messageBox.setIcon(messageBox.Warning)

        if exportCheckBoxState:  # if exportation in different files
            for ROIName, ROIDictValue in sorted(ROIDict.items()):
                directoryFolder = directory + '/' + ROIName
                if not os.path.exists(directoryFolder):
                    os.mkdir(directoryFolder)
                for fieldName, modelDict in sorted(ROIDictValue.items()):
                    filename = directoryFolder + '/' + fieldName + '.csv'
                    if os.path.exists(filename):
                        messageBox.setText('On folder ' + ROIName + ', file ' + fieldName + '.csv already exists.')
                        messageBox.setInformativeText('Do you want to replace it on ' + ROIName + '?')
                        messageBox.setStandardButtons(messageBox.NoToAll | messageBox.No | messageBox.YesToAll | messageBox.Yes)
                        choice = messageBox.exec_()
                        if choice == messageBox.NoToAll:
                            return True
                        if choice == messageBox.Yes:
                            self.exportFieldAsCSV(filename, fieldName, modelDict)
                        if choice == messageBox.YesToAll:
                            for ROIName, ROIDictValue in sorted(ROIDict.items()):
                                directoryFolder = directory + '/' + ROIName
                                if not os.path.exists(directoryFolder):
                                    os.mkdir(directoryFolder)
                                for fieldName, shapeDict in sorted(ROIDictValue.items()):
                                    filename = directoryFolder + '/' + fieldName + '.csv'
                                    self.exportFieldAsCSV(filename, fieldName, shapeDict)
                            return True
                    else:
                        self.exportFieldAsCSV(filename, fieldName, modelDict)
        else:
            for ROIName, ROIDictValue in sorted(ROIDict.items()):
                filename = directory + '/' + ROIName + '.csv'
                if os.path.exists(filename):
                    messageBox.setText('File ' + ROIName + '.csv already exists in this folder.')
                    messageBox.setInformativeText('Do you want to replace it? ')
                    messageBox.setStandardButtons(messageBox.NoToAll | messageBox.No | messageBox.YesToAll | messageBox.Yes)
                    choice = messageBox.exec_()
                    if choice == messageBox.NoToAll:
                        return True
                    if choice == messageBox.Yes:
                        self.exportAllAsCSV(filename, ROIName, ROIDictValue)
                    if choice == messageBox.YesToAll:
                        for ROIName, ROIDictValue in sorted(ROIDict.items()):
                            filename = directory + '/' + ROIName + '.csv'
                            self.exportAllAsCSV(filename, ROIName, ROIDictValue)
                        return True
                else:
                    self.exportAllAsCSV(filename, ROIName, ROIDictValue)

    def ExportationValueOnEachPoint(self,directoryExport, ROIDict):
        directory = directoryExport.directory
        directoryPointValuesFolder = directory + '/ValuesOnEachPoint'
        messageBox = ctk.ctkMessageBox()
        messageBox.setWindowTitle('WARNING')
        messageBox.setIcon(messageBox.Warning)
        if not os.path.exists(directoryPointValuesFolder):
            os.mkdir(directoryPointValuesFolder)
        for ROIName, ROIDictValue in sorted(ROIDict.items()):
            if ROIName != 'Entire Model':
                directoryFolder = directoryPointValuesFolder + '/' + ROIName
                if not os.path.exists(directoryFolder):
                    os.mkdir(directoryFolder)
                for fieldName, modelDict in sorted(ROIDictValue.items()):
                    directoryFilename = directoryFolder + '/' + fieldName
                    if not os.path.exists(directoryFilename):
                        os.mkdir(directoryFilename)
                    for modelName in modelDict.keys():
                        filename = directoryFilename + '/' + modelName + '.csv'
                        if os.path.exists(filename):
                            messageBox.setText('File ' + fieldName + '.csv already exist for the model ' + modelName)
                            messageBox.setInformativeText('Do you want to replace it on ?')
                            messageBox.setStandardButtons(messageBox.NoToAll | messageBox.No | messageBox.YesToAll | messageBox.Yes)
                            choice = messageBox.exec_()
                            if choice == messageBox.NoToAll:
                                return True
                            if choice == messageBox.Yes:
                                pointData = slicer.util.getNode(modelName).GetModelDisplayNode().GetInputPolyData().GetPointData()
                                fieldArray = pointData.GetArray(fieldName)
                                ROIArray = pointData.GetArray(ROIName)
                                self.exportPointValueAsCSV(filename, fieldArray, ROIArray)
                            if choice == messageBox.YesToAll:
                                for fieldName, modelDict in sorted(ROIDictValue.items()):
                                    for modelName in modelDict.keys():
                                        filename = directoryFilename + '/' + modelName + '.csv'
                                        pointData = slicer.util.getNode(modelName).GetModelDisplayNode().GetInputPolyData().GetPointData()
                                        fieldArray = pointData.GetArray(fieldName)
                                        ROIArray = pointData.GetArray(ROIName)
                                        self.exportPointValueAsCSV(filename, fieldArray, ROIArray)
                                return True
                        else:
                            pointData = slicer.util.getNode(modelName).GetModelDisplayNode().GetInputPolyData().GetPointData()
                            fieldArray = pointData.GetArray(fieldName)
                            ROIArray = pointData.GetArray(ROIName)
                            self.exportPointValueAsCSV(filename, fieldArray, ROIArray)


class MeshStatisticsTest(ScriptedLoadableModuleTest):
    def setUp(self):
        # reset the state - clear scene
        self.widget = slicer.modules.MeshStatisticsWidget
        slicer.mrmlScene.Clear(0)

    def runTest(self):
        # run all tests needed
        self.delayDisplay("Clear the scene")
        self.setUp()
        self.delayDisplay("Download and load datas")
        self.downloaddata()
        self.delayDisplay("Starting the tests")

        self.delayDisplay("Test1: Test Min Max Mean Functions")
        self.assertTrue(self.testMinMaxMeanFunctions())

        self.delayDisplay("Test2: Test Percentile Function")
        self.assertTrue(self.testPercentileFunction())

        self.delayDisplay("Test3: Test storage of Values Function")
        self.assertTrue(self.testStorageValue())

        self.delayDisplay("Test4: Test on entire models")
        self.delayDisplay("Test4-1: Test on T1toT2")
        self.assertTrue(self.testOnMesh(slicer.mrmlScene.GetNodesByName("T1toT2").GetItemAsObject(0),
                                        0, ["AbsolutePointToPointDistance",
                                            "PointToPointAlongZ",
                                            "SignedMagNormDirDistance",""],
                                        [[0.039, 5.766, 1.152, 0.821, 0.258, 0.459, 0.628, 0.959, 1.498, 1.726, 2.587],
                                         [-3.631, 1.187, -0.478, 0.787, -1.91, -1.278, -0.853, -0.335, 0.029, 0.218, 0.57],
                                         [-5.62, 0.947, -0.225, 0.786, -1.612, -0.541, -0.296, -0.037, 0.098, 0.238, 0.485],
                                         []],
                                        "Test4-1"))

        self.delayDisplay("Test4-2: Test on T1toT3")
        self.assertTrue(self.testOnMesh(slicer.mrmlScene.GetNodesByName("T1toT3").GetItemAsObject(0),
                                        0, ["AbsoluteMagNormDirDistance",
                                            "AbsolutePointToPointDistance",
                                            "PointToPointAlongY",
                                            "SignedPointToPointDistance",""],
                                        [[0.001, 6.14, 0.54, 0.779, 0.018, 0.06, 0.11, 0.266, 0.558, 0.903, 2.327],
                                         [0.016, 6.45, 1.696, 0.805, 0.347, 0.736, 1.161, 1.797, 2.213, 2.336, 2.825],
                                         [-4.919, 0.897, -0.15, 0.704, -1.195, -0.719, -0.532, -0.024, 0.356, 0.472, 0.613],
                                         [-6.45, 3.217, -0.218, 1.865, -2.78, -2.238, -1.943, -0.423, 1.696, 2.046, 2.301],
                                         []],
                                        "Test4-2"))
        self.delayDisplay("Test4-3: Test on T2toT3")
        self.assertTrue(self.testOnMesh(slicer.mrmlScene.GetNodesByName("T2toT3").GetItemAsObject(0),
                                        0, ["PointToPointAlongX",
                                            "PointToPointAlongY",
                                            "PointToPointAlongZ",""],
                                        [[-2.542, 2.153, -0.233, 0.933, -1.802, -1.341, -0.928, -0.067, 0.386, 0.647, 1.273],
                                         [-2.63, 2.266, 0.159, 0.923, -1.38, -0.903, -0.513, 0.309, 0.911, 1.074, 1.394],
                                         [-3.431, 1.172, -0.956, 0.924, -2.388, -2.04, -1.665, -0.915, -0.281, 0.047, 0.625],
                                         []],
                                        "Test4-3"))

        self.delayDisplay("Test5: Test on a ROI")
        self.delayDisplay("Test5-1: Test on T1toT2")
        self.assertTrue(self.testOnMesh(slicer.mrmlScene.GetNodesByName("T1toT2").GetItemAsObject(0),
                                        1, ["AbsolutePointToPointDistance",
                                            "PointToPointAlongZ",
                                            "SignedMagNormDirDistance",""],
                                        [[0.214, 4.152, 1.56, 0.671, 0.396, 0.927, 1.143, 1.584, 1.913, 2.059, 2.369],
                                         [-3.025, 1.159, -0.639, 0.986, -1.944, -1.676, -1.583, -0.294, 0.133, 0.394, 0.714],
                                         [-3.666, 0.947, -0.24, 0.807, -2.009, -0.666, -0.487, -0.076, 0.243, 0.377, 0.745],
                                         []],
                                        "Test5-1"))

        self.delayDisplay("Test5-2: Test on T1toT3")
        self.assertTrue(self.testOnMesh(slicer.mrmlScene.GetNodesByName("T1toT3").GetItemAsObject(0),
                                        1, ["AbsoluteMagNormDirDistance",
                                            "AbsolutePointToPointDistance",
                                            "PointToPointAlongY",
                                            "SignedPointToPointDistance",""],
                                        [[0.001, 4.031, 0.887, 0.98, 0.06, 0.146, 0.238, 0.519, 0.936, 2.247, 3.16],
                                         [1.529, 4.344, 2.293, 0.553, 1.623, 1.784, 1.889, 2.175, 2.537, 2.868, 3.41],
                                         [-3.537, 0.806, -0.515, 0.914, -2.425, -1.482, -0.893, -0.256, 0.131, 0.282, 0.557],
                                         [-4.344, 2.74, -1.265, 1.991, -3.41, -2.868, -2.463, -2.051, 1.582, 1.73, 2.348],
                                         []],
                                        "Test5-2"))
        self.delayDisplay("Test5-3: Test on T2toT3")
        self.assertTrue(self.testOnMesh(slicer.mrmlScene.GetNodesByName("T2toT3").GetItemAsObject(0),
                                        1, ["PointToPointAlongX",
                                            "PointToPointAlongY",
                                            "PointToPointAlongZ",""],
                                        [[-2.542, 2.153, 0.203, 1.306, -1.964, -1.56, -0.875, 0.473, 1.218, 1.684, 1.997],
                                         [-2.593, 1.354, -0.315, 1.02, -2.04, -1.306, -1.125, -0.319, 0.649, 0.853, 0.978],
                                         [-3.431, 0.582, -1.32, 1.04, -2.994, -2.212, -2.095, -1.62, -0.202, -0.109, 0.026],
                                         []],
                                        "Test5-3"))

        self.delayDisplay("All test passed!")

    def downloaddata(self):
        import urllib.request
        downloads = (
            ('http://slicer.kitware.com/midas3/download?items=240003', 'T1toT2.vtk', slicer.util.loadModel),
            ('http://slicer.kitware.com/midas3/download?items=240002', 'T1toT3.vtk', slicer.util.loadModel),
            ('http://slicer.kitware.com/midas3/download?items=240001', 'T2toT3.vtk', slicer.util.loadModel),
        )
        for url, name, loader in downloads:
            filePath = slicer.app.temporaryPath + '/' + name
            print(filePath)
            if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
                logging.info('Requesting download %s from %s...\n' % (name, url))
                urllib.request.urlretrieve(url, filePath)
            if loader:
                logging.info('Loading %s...' % (name,))
                loader(filePath)

        layoutManager = slicer.app.layoutManager()
        threeDWidget = layoutManager.threeDWidget(0)
        threeDView = threeDWidget.threeDView()
        threeDView.resetFocalPoint()
    
    def defineArrays(self, logic, firstValue, lastValue):
        arrayValue = vtk.vtkDoubleArray()
        ROIArray = vtk.vtkDoubleArray()
        for i in range(firstValue, lastValue):
            arrayValue.InsertNextValue(i)
            ROIArray.InsertNextValue(1.0)
        bool, array = logic.defineArray(arrayValue, ROIArray)
        if bool :
            return array
        return False

    def testStorageValue(self):
        logic = MeshStatisticsLogic()
        print(' Test storage of Values: ')
        arrayValue = vtk.vtkDoubleArray()
        arrayMask = vtk.vtkDoubleArray()
        for i in range(0, 1000, 2):
            arrayValue.InsertNextValue(i)
            arrayValue.InsertNextValue(i)
            arrayMask.InsertNextValue(0.0)
            arrayMask.InsertNextValue(0.0)
        listOfRandomNumber = list()
        del listOfRandomNumber[:]
        for i in range(0, 250):
            listOfRandomNumber.append(randint(0, 998))
        
        listOfRandomNumber = list(set(listOfRandomNumber))
        listOfRandomNumber = sorted(listOfRandomNumber)
        for index in listOfRandomNumber:
            arrayMask.SetValue(index, 1.0)
        bool, array = logic.defineArray(arrayValue, arrayMask)
        array = sorted(array)
        a = 0
        for i in listOfRandomNumber:
            if arrayValue.GetValue(i) != array[a]:
                print('        Failed', a, array[a], i, arrayValue.GetValue(i))
                return False
            a += 1
        print('         Passed')
        return True
            
    def testMinMaxMeanFunctions(self):
        logic = MeshStatisticsLogic()
        print('Test min, max, mean, and std: ')
        array = self.defineArrays(logic, 1, 1001)
        min, max = logic.computeMinMax(array)
        mean = logic.computeMean(array)
        std = logic.computeStandardDeviation(array)
        print('min=', min, 'max=', max, 'mean=', mean, 'std=', std)
        if min != 1.0 or max != 1000.0 or mean != 500.5 or std != 288.675:
            print('      Failed! ')
            return False
        else:
            print('      Passed! ')
        return True

    def testPercentileFunction(self):
        logic = MeshStatisticsLogic()
        print(' TEST Percentile ')

        # odd number of value:
        print('     TEST odd number of values ')
        array = self.defineArrays(logic, 0, 1001)
        quantiles = logic.computeQuantiles(array)
        actual = tuple(quantiles)
        expected = (50, 150, 250, 500, 750, 850, 950)

        if actual != expected:
            print('         Failed ! ')
            return False
        else:
            print('         Passed')

        # even number of value:
        print('     TEST even number of values ')
        array = self.defineArrays(logic, 1, 1001)
        quantiles = logic.computeQuantiles(array)
        actual = tuple(quantiles)
        expected = (50.95, 150.85, 250.75, 500.50, 750.25, 850.15, 950.05)

        if actual != expected:
            print('         Failed ! ')
            return False
        else:
            print('         Passed! ')
        return True

    def testOnMesh(self, model, indexOfTheRegionConsidered, fieldToCheck, measurements, NameOftheTest):
        self.widget.inputComboBox.setCheckState(model, 2)
        self.widget.ROIComboBox.setCurrentIndex(indexOfTheRegionConsidered)
        for i in range(0, 7):
            widget = self.widget.tableField.cellWidget(i, 0)
            widget.setChecked(True)
            self.widget.runButton.click()

        for ROIName, ROIDictValue in self.widget.ROIDict.items():
            i = 0
            for fieldName, modelDict in sorted(ROIDictValue.items()):
                if fieldName == fieldToCheck[i]:
                    self.delayDisplay(NameOftheTest + "-" + str(i+1) + ": test on " + fieldName)
                    for a in modelDict.items():
                        if measurements[i] != [a[1].min, a[1].max, a[1].mean, a[1].std, a[1].percentile5,
                           a[1].percentile15, a[1].percentile25, a[1].percentile50, a[1].percentile75,
                           a[1].percentile85, a[1].percentile95]:
                            print(measurements[i])
                            print([a[1].min, a[1].max, a[1].mean, a[1].std, a[1].percentile5,
                           a[1].percentile15, a[1].percentile25, a[1].percentile50, a[1].percentile75,
                           a[1].percentile85, a[1].percentile95])
                            return False
                    i = i + 1

        self.widget.inputComboBox.setCheckState(model, 0)
        return True
