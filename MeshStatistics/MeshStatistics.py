import numpy
import math
import re
import csv
import os
from __main__ import vtk, qt, ctk, slicer
from random import randint
from slicer.ScriptedLoadableModule import *

class MeshStatistics(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        parent.title = 'Mesh Statistics'
        parent.categories = ['Shape Analysis']
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
        # -------------------------------------------------------------------------------------
        self.modelList = list()
        self.fieldList = list()
        self.ROIList = list()
        self.ROIDict = dict()  # Key = Name of ROI
                               # Value = Dictionary of Fields (key = Name of Field
                               #                               Value = dictionary of shapes
                               #                                             key = name of shapes
                               #                                             value = Statistics store()

        self.logic = MeshStatisticsLogic()
        # ------------------------------------------------------------------------------------
        #                                    SHAPES INPUT
        # ------------------------------------------------------------------------------------
        self.inputComboBox = slicer.qMRMLCheckableNodeComboBox()
        self.inputComboBox.nodeTypes = ['vtkMRMLModelNode']
        self.inputComboBox.setMRMLScene(slicer.mrmlScene)
        inputLayout = qt.QFormLayout()
        inputLayout.addRow(' Models: ', self.inputComboBox)
        self.layout.addLayout(inputLayout)

        self.inputComboBox.connect('checkedNodesChanged()', self.onInputComboBoxCheckedNodesChanged)
        # ------------------------------------------------------------------------------------
        #                                  ROI TABLE
        # ------------------------------------------------------------------------------------
        self.ROIComboBox = ctk.ctkComboBox()
        self.ROIComboBox.adjustSize()
        self.ROICheckBox = qt.QCheckBox('All')
        ROILayout = qt.QHBoxLayout()
        ROILayout_0 = qt.QFormLayout()
        ROILayout_0.addRow(' Region considered: ', self.ROIComboBox)
        ROILayout.addLayout(ROILayout_0)
        ROILayout.addWidget(self.ROICheckBox)

        self.layout.addLayout(ROILayout)
        self.ROICheckBox.connect('stateChanged(int)', self.onROICheckBoxStateChanged)
        # ------------------------------------------------------------------------------------
        #                                  FIELD TABLE
        # ------------------------------------------------------------------------------------
        self.tableField = qt.QTableWidget()
        self.tableField.setColumnCount(2)
        self.tableField.setMinimumHeight(250)
        self.tableField.setHorizontalHeaderLabels([' ', ' Field Name '])
        self.tableField.setColumnWidth(0, 20)
        self.tableField.setColumnWidth(1, 260)
        self.tableField.setSizePolicy(qt.QSizePolicy().Expanding, qt.QSizePolicy().Expanding)
        
        label = qt.QLabel(' Select a Field to compute statistics on:')
        self.fieldLayout = qt.QVBoxLayout()
        self.fieldLayout.addWidget(label)
        self.fieldLayout.addWidget(self.tableField)
        self.layout.addLayout(self.fieldLayout)
        # ------------------------------------------------------------------------------------
        #                                    RUN
        # ------------------------------------------------------------------------------------
        self.runButton = qt.QPushButton(' Run ')
        self.runButton.enabled = False
        roiLayout = qt.QHBoxLayout()
        roiLayout.addWidget(self.runButton)
        self.layout.addLayout(roiLayout)
        self.runButton.connect('clicked()', self.onRunButton)
        # ------------------------------------------------------------------------------------
        #                          Statistics Table - Export
        # ------------------------------------------------------------------------------------
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
        self.logic.updateInterface(self.tableField, self.ROIComboBox, self.ROIList, self.modelList, self.layout)

        # ------------------------------------------------------------------------------------
        #                                   OBSERVERS
        # ------------------------------------------------------------------------------------
        def onCloseScene(obj, event):
            # initialize Parameters
            globals()['MeshStatistics'] = slicer.util.reloadScriptedModule('MeshStatistics')
        slicer.mrmlScene.AddObserver(slicer.mrmlScene.EndCloseEvent, onCloseScene)

    def onInputComboBoxCheckedNodesChanged(self):
        self.modelList = self.inputComboBox.checkedNodes()
        self.runButton.enabled = not self.inputComboBox.noneChecked()
        self.logic.updateInterface(self.tableField, self.ROIComboBox, self.ROIList, self.modelList, self.layout)

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
            self.logic.removeTable(self.layout, self.tabROI)
            self.exportButton.disconnect('clicked()', self.onExportButton)
            self.layout.removeWidget(self.exportButton)
            self.layout.removeItem(self.exportLayout)
        self.logic.displayStatistics(self.ROICheckBox.isChecked(), self.ROIList, self.ROIDict, self.ROIComboBox,
                                     self.tableField, self.modelList, self.tabROI, self.layout)
        self.layout.addLayout(self.exportLayout)
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

    def __init__(self):
        self.numberOfDecimals = 3

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
            label.setStyleSheet(' qproperty-alignment: AlignCenter; }')
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
        statTable.setMinimumHeight(numberOfRows*35)
        statTable.setMinimumWidth(55)

        statTable.setColumnCount(12)
        statTable.setHorizontalHeaderLabels(['Model','Min','Max','Mean','SD','Per5','Per15','Per25','Per50','Per75','Per85','Per95'])
        # Add Values:
        for key, value in fieldDictionaryValue.iteritems():
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
        for ROIName, FieldDict in ROIDict.iteritems():
            tab = qt.QTabWidget()
            tab.adjustSize()
            tab.setTabPosition(1)
            for fieldName, fieldDictValue in FieldDict.iteritems():
                statisticsTable = self.defineStatisticsTable(fieldDictValue)
                tab.addTab(statisticsTable, fieldName)
            tabROI.addTab(tab, ROIName)
        layout.addWidget(tabROI)

    def displayStatistics(self, ROICheckBoxState, ROIList, ROIDict, ROIComboBox, tableField, modelList, tabROI, layout):
        if ROICheckBoxState:
            for ROIName in ROIList:
                if not ROIDict.has_key(ROIName):
                    ROIDict[ROIName] = dict()
        else:
            ROIToCompute = ROIComboBox.currentText.encode('utf-8')
            if not ROIDict.has_key(ROIToCompute):
                ROIDict[ROIToCompute] = dict()
                
        numberOfRowField = tableField.rowCount
        for ROIName, ROIFieldDict in ROIDict.iteritems():
            for i in range(0, numberOfRowField):
                widget = tableField.cellWidget(i, 0)
                if widget and widget.isChecked():
                    ROIFieldDict[tableField.cellWidget(i, 1).text.encode('utf-8')] = dict()
            for fieldName, fieldValue in ROIFieldDict.iteritems():
                for shape in modelList:
                    activePointData = shape.GetModelDisplayNode().GetInputPolyData().GetPointData()
                    fieldArray = activePointData.GetArray(fieldName)
                    fieldValue[shape.GetName()] = self.StatisticStore()
                    if ROIName == 'Entire Model':
                        self.computeAll(fieldArray, fieldValue[shape.GetName()], 'None')
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
        if ROIArray == 'None':
            for i in range(0, fieldArray.GetNumberOfTuples()):
                valueList.append(fieldArray.GetValue(i))
            valueArray = numpy.array(valueList)
        else:
            if ROIArray.GetNumberOfTuples() != fieldArray.GetNumberOfTuples():
                print 'Size of ROIArray and fieldArray are not the same!!!'
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
    
    def computePercentile(self, valueArray, percent):
        #  Function to compute different percentile
        #  valueArray is an array in which values to compute statistics on are stored
        #  percent is a value between 0 and 1
        #  The lowest value is taken
        valueArray = numpy.sort(valueArray)
        index = (valueArray.size * percent) - 1
        ceilIndex = math.ceil(index)
        return round(valueArray[ceilIndex], self.numberOfDecimals)

    def computeAll(self, fieldArray, fieldState, ROIArray):
        bool, array = self.defineArray(fieldArray, ROIArray)
        if bool:
            fieldState.min, fieldState.max = self.computeMinMax(array)
            fieldState.mean = self.computeMean(array)
            fieldState.std = self.computeStandardDeviation(array)
            fieldState.percentile5 = self.computePercentile(array, 0.05)
            fieldState.percentile15 = self.computePercentile(array, 0.15)
            fieldState.percentile25 = self.computePercentile(array, 0.25)
            fieldState.percentile50 = self.computePercentile(array, 0.50)
            fieldState.percentile75 = self.computePercentile(array, 0.75)
            fieldState.percentile85 = self.computePercentile(array, 0.85)
            fieldState.percentile95 = self.computePercentile(array, 0.95)

    def writeFieldFile(self, fileWriter, modelDict):
        #  Function defined to export all statistics of a field concidering a file writer (fileWriter)
        #  and a dictionary of models (modelDict) where statistics are stored
        for shapeName, shapeStats in modelDict.iteritems():
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
        system = qt.QLocale().system()
        myDelimiter = chr(system.groupSeparator())
        decimalPoint = chr(system.decimalPoint())
        file = open(filename, 'w')
        cw = csv.writer(file, delimiter=myDelimiter)
        cw.writerow([ROIName])
        cw.writerow([' '])
        for fieldName, shapeDict in sorted(ROIDictValue.iteritems()):
            cw.writerow([fieldName])
            cw.writerow(['Model','Min','Max','Mean','SD','Per5','Per15','Per25','Per50','Per75','Per85','Per95'])
            self.writeFieldFile(cw, shapeDict)
            cw.writerow([' '])
        file.close()
        if decimalPoint != '.':
            self.replaceCharac(filename, '.', decimalPoint)

    def exportFieldAsCSV(self, filename, fieldName, shapeDict):
        #  Export fields on different csv files
        system = qt.QLocale().system()
        myDelimiter = chr(system.groupSeparator())
        decimalPoint = chr(system.decimalPoint())
        file = open(filename, 'w')
        cw = csv.writer(file, delimiter=myDelimiter)
        cw.writerow([fieldName])
        cw.writerow(['Model','Min','Max','Mean','SD','Per5','Per15','Per25','Per50','Per75','Per85','Per95'])
        self.writeFieldFile(cw, shapeDict)
        file.close()
        if decimalPoint != '.':
            self.replaceCharac(filename, '.', decimalPoint)
    
    def exportPointValueAsCSV(self, filename, fieldArray, ROIArray):
        #Exportation of the value stored for each point:
        system = qt.QLocale().system()
        myDelimiter = chr(system.groupSeparator())
        decimalPoint = chr(system.decimalPoint())
        file = open(filename, 'w')
        cw = csv.writer(file, delimiter=myDelimiter)
        bool, arrayToReturn = self.defineArray(fieldArray, ROIArray)
        if bool:
            for value in arrayToReturn:
                cw.writerow([value])
            file.close()
            if decimalPoint != '.':
                self.replaceCharac(filename, '.', decimalPoint)

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
        messageBox.setWindowTitle(' /!\ WARNING /!\ ')
        messageBox.setIcon(messageBox.Warning)

        if exportCheckBoxState:  # if exportation in different files
            for ROIName, ROIDictValue in sorted(ROIDict.iteritems()):
                directoryFolder = directory + '/' + ROIName
                if not os.path.exists(directoryFolder):
                    os.mkdir(directoryFolder)
                for fieldName, modelDict in sorted(ROIDictValue.iteritems()):
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
                            for ROIName, ROIDictValue in sorted(ROIDict.iteritems()):
                                directoryFolder = directory + '/' + ROIName
                                if not os.path.exists(directoryFolder):
                                    os.mkdir(directoryFolder)
                                for fieldName, shapeDict in sorted(ROIDictValue.iteritems()):
                                    filename = directoryFolder + '/' + fieldName + '.csv'
                                    self.exportFieldAsCSV(filename, fieldName, shapeDict)
                            return True
                    else:
                        self.exportFieldAsCSV(filename, fieldName, modelDict)
        else:
            for ROIName, ROIDictValue in sorted(ROIDict.iteritems()):
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
                        for ROIName, ROIDictValue in sorted(ROIDict.iteritems()):
                            filename = directory + '/' + ROIName + '.csv'
                            self.exportAllAsCSV(filename, ROIName, ROIDictValue)
                        return True
                else:
                    self.exportAllAsCSV(filename, ROIName, ROIDictValue)

    def ExportationValueOnEachPoint(self,directoryExport, ROIDict):
        directory = directoryExport.directory
        directoryPointValuesFolder = directory + '/ValuesOnEachPoint'
        messageBox = ctk.ctkMessageBox()
        messageBox.setWindowTitle(' /!\ WARNING /!\ ')
        messageBox.setIcon(messageBox.Warning)
        if not os.path.exists(directoryPointValuesFolder):
            os.mkdir(directoryPointValuesFolder)
        for ROIName, ROIDictValue in sorted(ROIDict.iteritems()):
            if ROIName != 'Entire Model':
                directoryFolder = directoryPointValuesFolder + '/' + ROIName
                if not os.path.exists(directoryFolder):
                    os.mkdir(directoryFolder)
                for fieldName, modelDict in sorted(ROIDictValue.iteritems()):
                    directoryFilename = directoryFolder + '/' + fieldName
                    if not os.path.exists(directoryFilename):
                        os.mkdir(directoryFilename)
                    for modelName in modelDict.iterkeys():
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
                                for fieldName, modelDict in sorted(ROIDictValue.iteritems()):
                                    for modelName in modelDict.iterkeys():
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
        slicer.mrmlScene.Clear(0)

    def runTest(self):
        self.setUp()
        self.delayDisplay(' Starting tests ')
        self.delayDisplay(' Test Min Max Mean Functions ')
        self.assertTrue(self.testMinMaxMeanFunctions())
        self.delayDisplay(' Test Percentile Function ')
        self.assertTrue(self.testPercentileFunction())
        self.delayDisplay(' Test storage of Values Function ')
        self.assertTrue(self.testStorageValue())
        self.delayDisplay(' Tests Passed! ')
    
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
        print ' Test storage of Values: '
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
                print '        Failed', a, array[a], i, arrayValue.GetValue(i)
                return False
            a += 1
        print '         Passed'
        return True
            
    def testMinMaxMeanFunctions(self):
        logic = MeshStatisticsLogic()
        print 'Test min, max, mean, and std: '
        array = self.defineArrays(logic, 1, 1001)
        min, max = logic.computeMinMax(array)
        mean = logic.computeMean(array)
        std = logic.computeStandardDeviation(array)
        print 'min=', min, 'max=', max, 'mean=', mean, 'std=', std
        if min != 1.0 or max != 1000.0 or mean != 500.5 or std != 288.675:
            print '      Failed! '
            return False
        else:
            print '      Passed! '
        return True

    def testPercentileFunction(self):
        logic = MeshStatisticsLogic()
        # pair number of value:
        print ' TEST Percentile '
        print '     TEST Pair number of values '
        array = self.defineArrays(logic, 1, 1001)
        percentile5 = logic.computePercentile(array, 0.05)
        percentile15 = logic.computePercentile(array, 0.15)
        percentile25 = logic.computePercentile(array, 0.25)
        percentile50 = logic.computePercentile(array, 0.50)
        percentile75 = logic.computePercentile(array, 0.75)
        percentile85 = logic.computePercentile(array, 0.85)
        percentile95 = logic.computePercentile(array, 0.95)
        if percentile5 != 50 or percentile15 != 150 or percentile25 != 250 or percentile50 != 500 or percentile75 != 750 or percentile85 != 850 or percentile95 != 950:
            print '         Failed ! '
            return False
        else:
            print '         Passed'
        # odd number of value:
        print '     TEST Odd number of values '
        array = self.defineArrays(logic, 1, 1000)
        percentile5 = logic.computePercentile(array, 0.05)
        percentile15 = logic.computePercentile(array, 0.15)
        percentile25 = logic.computePercentile(array, 0.25)
        percentile50 = logic.computePercentile(array, 0.50)
        percentile75 = logic.computePercentile(array, 0.75)
        percentile85 = logic.computePercentile(array, 0.85)
        percentile95 = logic.computePercentile(array, 0.95)
        if percentile5 != 50 or percentile15 != 150 or percentile25 != 250 or percentile50 != 500 or percentile75 != 750 or percentile85 != 850 or percentile95 != 950:
            print '         Failed ! '
            return False
        else:
            print '         Passed! '
        return True