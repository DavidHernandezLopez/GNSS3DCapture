# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GNSS3DCaptureDockWidget
                                 A QGIS plugin
 A plugin for capture 3D points from GNSS equipment
                             -------------------
        begin                : 2016-10-05
        git sha              : $Format:%H$
        copyright            : (C) 2016 by David Hernández López, Insittuto de Desarrollo Regional - UCLM
        email                : david.hernandez@uclm.es
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os
import os,sys
import shutil
reload(sys)
sys.setdefaultencoding("utf-8")

from PyQt4 import QtGui, uic
from PyQt4.QtCore import pyqtSignal
from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import QgsApplication,QgsCoordinateReferenceSystem
from qgis.core import *
from qgis.core import (QgsGPSDetector, QgsGPSConnectionRegistry, QgsPoint, \
                        QgsCoordinateTransform, QgsCoordinateReferenceSystem, \
                        QgsGPSInformation)
from qgis.core import QgsRasterLayer
from qgis.core import QgsRaster
from qgis.core import QgsField,QgsFeature,QgsGeometry
from qgis.core import QgsVectorLayer
from qgis.core import QgsMapLayerRegistry
from PyQt4.QtCore import QVariant
from gnss_3d_capture_configure_dialog import *

from math import floor
import re

import constants

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'gnss_3d_capture_dockwidget_base.ui'))


class GNSS3DCaptureDockWidget(QtGui.QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self,
                 iface,
                 parent=None):
        """Constructor."""
        super(GNSS3DCaptureDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.iface = iface
        self.initialize()

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def finishProcess(self):
        self.capturePointGroupBox.setEnabled(False)
        self.nameLineEdit.clear()
        self.numberLineEdit.clear()
        self.codeLineEdit.clear()
        self.firstCoordinateLineEdit.clear()
        self.secondCoordinateLineEdit.clear()
        self.heightAntennaLineEdit.clear()
        self.heightGpsLineEdit.clear()
        self.heightGroundLineEdit.clear()
        self.heightGeoidLineEdit.clear()
        self.heightFromGeoidLineEdit.clear()
        self.configurePushButton.setEnabled(True)
        self.startPushButton.setEnabled(False)
        self.finishPushButton.setEnabled(False)

    def getGeoidInterpolatedValue(self,
                                  gpsLongitude,
                                  gpsLatitude):
        geoidPoint = QgsPoint(gpsLongitude,gpsLatitude)
        geoidPoint = self.crsOperationFromGpsToGeoid.transform(geoidPoint)
        geoidHeight = constants.CONST_GNSS_3D_CAPTURE_GEOIDS_NO_VALUE
        if not self.geoidModel.extent().contains(geoidPoint):
            msgBox=QMessageBox(self)
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setWindowTitle(constants.CONST_GNSS_3D_CAPTURE_WINDOW_TITLE)
            msgBox.setText("Point out of Geoid Model extension:\n",self.geoidModelFileName)
            msgBox.exec_()
            return geoidHeight
        firstCoordinate = geoidPoint.x()
        secondCoordinate = geoidPoint.y()
        dbl_column = (firstCoordinate - self.geoidMinimumFirstCoordinate) / self.geoidStepFirstCoordinate
        dbl_row = (secondCoordinate - self.geoidMaximumSecondCoordinate) / self.geoidStepSecondCoordinate
        inc_column = dbl_column - floor(dbl_column)
        inc_row = dbl_row - floor(dbl_row)
        f00 = self.getGeoidPixelValue(firstCoordinate, secondCoordinate)
        if f00 == constants.CONST_GNSS_3D_CAPTURE_GEOIDS_NO_VALUE:
            return geoidHeight
        f10 = self.getGeoidPixelValue(firstCoordinate + self.geoidStepFirstCoordinate, secondCoordinate)
        if f10 == constants.CONST_GNSS_3D_CAPTURE_GEOIDS_NO_VALUE:
            return geoidHeight
        f01 = self.getGeoidPixelValue(firstCoordinate, secondCoordinate + self.geoidStepSecondCoordinate)
        if f01 == constants.CONST_GNSS_3D_CAPTURE_GEOIDS_NO_VALUE:
            return geoidHeight
        f11 = self.getGeoidPixelValue(firstCoordinate + self.geoidStepFirstCoordinate, secondCoordinate + self.geoidStepSecondCoordinate)
        if f11 == constants.CONST_GNSS_3D_CAPTURE_GEOIDS_NO_VALUE:
            return geoidHeight
        geoidHeight = (1.0 - inc_row) * (1.0 - inc_column) * f00
        geoidHeight += inc_column * (1.0 - inc_row) * f10
        geoidHeight += (1.0 - inc_column) * inc_row * f01
        geoidHeight += inc_column * inc_row * f11
        return geoidHeight

    def getGeoidPixelValue(self,
                           gpsLongitude,
                           gpsLatitude):
        geoidPoint = QgsPoint(gpsLongitude,gpsLatitude)
        geoidPoint = self.crsOperationFromGpsToGeoid.transform(geoidPoint)
        geoidHeight = constants.CONST_GNSS_3D_CAPTURE_GEOIDS_NO_VALUE
        if not self.geoidModel.extent().contains(geoidPoint):
            msgBox=QMessageBox(self)
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setWindowTitle(constants.CONST_GNSS_3D_CAPTURE_WINDOW_TITLE)
            msgBox.setText("Point out of Geoid Model extension:\n",self.geoidModelFileName)
            msgBox.exec_()
            return geoidHeight
        firstCoordinate = geoidPoint.x()
        secondCoordinate = geoidPoint.y()
        ident = self.geoidModel.dataProvider().identify(geoidPoint,QgsRaster.IdentifyFormatValue)
        if ident.isValid():
            values = ident.results()
            geoidHeight = values[1]
        else:
            msgBox=QMessageBox(self)
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setWindowTitle(constants.CONST_GNSS_3D_CAPTURE_WINDOW_TITLE)
            msgBox.setText("Error getting value in Geoid Model:\n",self.geoidModelFileName)
            msgBox.exec_()
        return geoidHeight

    def initialize(self):
        aux_path_plugin = 'python/plugins/' + constants.CONST_GNSS_3D_CAPTURE_NAME
        qgisUserDbFilePath = QgsApplication.qgisUserDbFilePath()
        self.path_plugin = os.path.join(QFileInfo(QgsApplication.qgisUserDbFilePath()).path(),aux_path_plugin)
        path_file_qsettings = self.path_plugin + '/' +constants.CONST_GNSS_3D_CAPTURE_SETTINGS_FILE_NAME
        self.settings = QSettings(path_file_qsettings,QSettings.IniFormat)
        self.lastPath = self.settings.value("last_path")
        if not self.lastPath:
            self.lastPath = QDir.currentPath()
            self.settings.setValue("last_path",self.lastPath)
            self.settings.sync()
        self.crsAuthId=self.settings.value("crsAuthId")
        if not self.crsAuthId:
            self.crsAuthId = self.iface.mapCanvas().mapRenderer().destinationCrs().authid()
            self.settings.setValue("crsAuthId",self.crsAuthId)
            self.settings.sync()
        self.crs=QgsCoordinateReferenceSystem()
        self.crs.createFromUserInput(self.crsAuthId)
        if self.crs.geographicFlag():
            self.firstCoordinateLabel.setText("Longitude")
            self.secondCoordinateLabel.setText("Latitude")
        else:
            self.firstCoordinateLabel.setText("Easting")
            self.secondCoordinateLabel.setText("Northing")
        self.iface.mapCanvas().mapRenderer().setProjectionsEnabled(True)
        self.startPushButton.setEnabled(False)
        self.finishPushButton.setEnabled(False)
        self.capturePointGroupBox.setEnabled(False)
        QtCore.QObject.connect(self.configurePushButton,QtCore.SIGNAL("clicked(bool)"),self.selectConfigure)
        # QtCore.QObject.connect(self.crsPushButton,QtCore.SIGNAL("clicked(bool)"),self.selectCrs)
        # QtCore.QObject.connect(self.geoidCheckBox,QtCore.SIGNAL("clicked(bool)"),self.activateGeoid)
        QtCore.QObject.connect(self.startPushButton,QtCore.SIGNAL("clicked(bool)"),self.startProcess)
        QtCore.QObject.connect(self.updatePositionPushButton,QtCore.SIGNAL("clicked(bool)"),self.updatePosition)
        QtCore.QObject.connect(self.finishPushButton,QtCore.SIGNAL("clicked(bool)"),self.finishProcess)
        QtCore.QObject.connect(self.savePointPushButton,QtCore.SIGNAL("clicked(bool)"),self.savePoint)
        QtCore.QObject.connect(self.codePushButton,QtCore.SIGNAL("clicked(bool)"),self.selectCode)
        QtCore.QObject.connect(self.namePushButton,QtCore.SIGNAL("clicked(bool)"),self.selectName)
        QtCore.QObject.connect(self.numberPushButton,QtCore.SIGNAL("clicked(bool)"),self.selectNumber)
        QtCore.QObject.connect(self.heightAntennaPushButton,QtCore.SIGNAL("clicked(bool)"),self.selectAntennaHeight)
        self.pointNumbers = []
        #self.configureDialog = None
        self.configureDialog = GNSS3DCaptureDialog(self.iface,self.lastPath,self.crs)
        self.num_format = re.compile(r'^\-?[1-9][0-9]*\.?[0-9]*')

    def savePoint(self):
        connectionRegistry = QgsGPSConnectionRegistry().instance()
        connectionList = connectionRegistry.connectionList()
        if connectionList == []:
            msgBox=QMessageBox(self)
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setWindowTitle(constants.CONST_GNSS_3D_CAPTURE_WINDOW_TITLE)
            msgBox.setText("GPS connection not detected.\nConnect a GPS and try again")
            msgBox.exec_()
            return
        csvFile=QFile(self.csvFileName)
        if not csvFile.open(QIODevice.Append | QIODevice.Text):
            msgBox=QMessageBox(self)
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setWindowTitle(constants.CONST_GNSS_3D_CAPTURE_WINDOW_TITLE)
            msgBox.setText("Error opening for writting file:\n"+self.csvFileName)
            msgBox.exec_()
            return
        csvTextStream = QTextStream(csvFile)
        csvTextStream<<"\n"
        fieldValues={}
        fieldNumber = 0
        listFieldValues = []
        if self.useName:
            name = self.nameLineEdit.text()
            csvTextStream<<name<<","
            #fieldValues[fieldNumber]=QVariant(name)
            fieldValues[fieldNumber]=name
            fieldNumber = fieldNumber +1
            listFieldValues.append(name)
        if self.useNumber:
            number = self.numberLineEdit.text()
            csvTextStream<<number<<","
            #fieldValues[fieldNumber]=QVariant(number)
            fieldValues[fieldNumber]=number
            fieldNumber = fieldNumber +1
            listFieldValues.append(number)
        GPSInfo = connectionList[0].currentGPSInformation()
        firstCoordinate = GPSInfo.longitude
        secondCoordinate = GPSInfo.latitude
        pointCrsGps = QgsPoint(firstCoordinate,secondCoordinate)
        pointCrs = self.crsOperationFromGps.transform(pointCrsGps)
        firstCoordinate = pointCrs.x()
        secondCoordinate = pointCrs.y()
        if self.crs.geographicFlag():
            strFirstCoordinate = constants.CONST_GNSS_3D_CAPTURE_SAVE_POINT_LONGITUDE_PRECISION.format(firstCoordinate)
            strSecondCoordinate = constants.CONST_GNSS_3D_CAPTURE_SAVE_POINT_LATITUDE_PRECISION.format(secondCoordinate)
        else:
            strFirstCoordinate = constants.CONST_GNSS_3D_CAPTURE_SAVE_POINT_EASTING_PRECISION.format(firstCoordinate)
            strSecondCoordinate = constants.CONST_GNSS_3D_CAPTURE_SAVE_POINT_NORTHING_PRECISION.format(secondCoordinate)
        csvTextStream<<strFirstCoordinate<<","
        csvTextStream<<strSecondCoordinate
        #fieldValues[fieldNumber]=QVariant(firstCoordinate)
        fieldValues[fieldNumber]=firstCoordinate
        listFieldValues.append(firstCoordinate)
        fieldNumber = fieldNumber +1
        #fieldValues[fieldNumber]=QVariant(secondCoordinate)
        fieldValues[fieldNumber]=secondCoordinate
        listFieldValues.append(secondCoordinate)
        fieldNumber = fieldNumber +1
        if self.useHeight:
            antennaHeight = float(self.heightAntennaLineEdit.text())
            height = GPSInfo.elevation
            height = height - antennaHeight
            if self.useGeoidModel:
                geoidHeight = self.getGeoidInterpolatedValue(GPSInfo.longitude,GPSInfo.latitude)
                if geoidHeight == constants.CONST_GNSS_3D_CAPTURE_GEOIDS_NO_VALUE:
                    return
                height = height - geoidHeight
            strHeight=constants.CONST_GNSS_3D_CAPTURE_SAVE_POINT_HEIGHT_PRECISION.format(height)
            csvTextStream<<","<<strHeight
            #fieldValues[fieldNumber]=QVariant(height)
            fieldValues[fieldNumber]=height
            listFieldValues.append(height)
            fieldNumber = fieldNumber +1
        if self.useCode:
            code = self.codeLineEdit.text()
            csvTextStream<<","<<code
            #fieldValues[fieldNumber]=QVariant(code)
            fieldValues[fieldNumber]=code
            listFieldValues.append(code)
        csvFile.close()
        fet = QgsFeature()
        fet.setGeometry( QgsGeometry.fromPoint(QgsPoint(firstCoordinate,secondCoordinate)) )
        #fet.setAttributeMap(fieldValues)
        fet.setAttributes(listFieldValues)
        self.memoryLayerDataProvider.addFeatures([fet])
        self.memoryLayer.commitChanges()
        if self.useNumber:
            self.pointNumbers.append(int(number))
            candidateValue = self.pointNumbers[len(self.pointNumbers) - 1] + 1
            if self.pointNumbers.count(candidateValue)!= 0:
                control = True
                while control:
                    candidateValue = candidateValue + 1
                    if self.pointNumbers.count(candidateValue) == 0:
                        control = False
            self.numberLineEdit.setText(str(candidateValue))
        self.accept()

    def selectCode(self):
        oldText = self.codeLineEdit.text()
        label = "Input Point Code:"
        title = constants.CONST_GNSS_3D_CAPTURE_SAVE_POINT_WINDOW_TITLE
        [text, ok] = QInputDialog.getText(self, title, label, QLineEdit.Normal, oldText)
        if ok and text:
            text = text.strip()
            if not text == oldText:
                self.codeLineEdit.setText(text)

    def selectAntennaHeight(self):
        strCandidateValue = self.heightAntennaLineEdit.text()
        label = "Input Antenna Height:"
        title = constants.CONST_GNSS_3D_CAPTURE_SAVE_POINT_WINDOW_TITLE
        ok = False
        while not ok:
            [text, ok] = QInputDialog.getText(self, title, label, QLineEdit.Normal, strCandidateValue)
            if ok and text:
                value = 0.0
                text = text.strip()
                if text.isdigit() or re.match(self.num_format,text):
                    value = float(text)
                    if (value < constants.CONST_GNSS_3D_CAPTURE_SAVE_POINT_ANTENNA_HEIGHT_MINIMUM_VALUE
                        or value > constants.CONST_GNSS_3D_CAPTURE_SAVE_POINT_ANTENNA_HEIGHT_MAXIMUM_VALUE):
                        ok = False
                else:
                    ok = False
                if ok:
                    strValue=constants.CONST_GNSS_3D_CAPTURE_SAVE_POINT_ANTENNA_HEIGHT_PRECISION.format(value)
                    self.heightAntennaLineEdit.setText(strValue)
                    self.updatePosition()
            else:
                if not ok:
                    ok = True

    def selectConfigure(self):
        # if self.configureDialog == None:
        #     self.configureDialog = GNSS3DCaptureDialog(self.iface,self.lastPath,self.crs)
        #     self.configureDialog.show() # show the dialog
        #     result = self.configureDialog.exec_() # Run the dialog
        #     yo =1
        # else:
        #     self.configureDialog.show() # show the dialog
        #     result = self.configureDialog.exec_() # Run the dialog
        #     yo =1
#        if self.configureDialog.isOk():
        self.configureDialog.show() # show the dialog
        result = self.configureDialog.exec_() # Run the dialog
        self.csvFileName=self.configureDialog.getCsvFileName()
        self.lastPath = self.configureDialog.getLastPath()
        self.crs = self.configureDialog.getCrs()
        self.useCode = self.configureDialog.getUseCode()
        self.useName = self.configureDialog.getUseName()
        self.useHeight = self.configureDialog.getUseHeight()
        self.useNumber = self.configureDialog.getUseNumber()
        self.useGeoidModel = self.configureDialog.getUseGeoidModel()
        self.geoidModelFileName = self.configureDialog.getGeoidModelFileName()
        if self.crs.isValid():
            if self.crs.geographicFlag():
                self.firstCoordinateLabel.setText("Longitude")
                self.secondCoordinateLabel.setText("Latitude")
            else:
                self.firstCoordinateLabel.setText("Easting")
                self.secondCoordinateLabel.setText("Northing")
            crsAuthId = self.crs.authid()
            self.settings.setValue("crsAuthId",crsAuthId)
            self.settings.sync()
        if self.lastPath:
            self.settings.setValue("last_path",self.lastPath)
            self.settings.sync()
        if self.configureDialog.getIsOk():
            self.startPushButton.setEnabled(True)
        else:
            self.startPushButton.setEnabled(False)

    def selectName(self):
        oldText = self.nameLineEdit.text()
        label = "Input Point Name:"
        title = constants.CONST_GNSS_3D_CAPTURE_SAVE_POINT_WINDOW_TITLE
        [text, ok] = QInputDialog.getText(self, title, label, QLineEdit.Normal, oldText)
        if ok and text:
            text = text.strip()
            if not text == oldText:
                self.nameLineEdit.setText(text)

    def selectNumber(self):
        if self.pointNumbers == []:
            candidateValue = constants.CONST_GNSS_3D_CAPTURE_SAVE_POINT_FIRST_POINT_NUMBER
        else:
            candidateValue = self.pointNumbers(len(self.pointNumbers) - 1)
        label = "Input Point Number:"
        title = constants.CONST_GNSS_3D_CAPTURE_SAVE_POINT_WINDOW_TITLE
        ok = False
        while not ok:
            [text, ok] = QInputDialog.getText(self, title, label, QLineEdit.Normal, str(candidateValue))
            if ok and text:
                text = text.strip()
                if not text.isdigit():
                    ok = False
                else:
                    value = int(text)
                    if (value < constants.CONST_GNSS_3D_CAPTURE_SAVE_POINT_POINT_NUMBER_MINIMUM_VALUE
                        or value > constants.CONST_GNSS_3D_CAPTURE_SAVE_POINT_POINT_NUMBER_MAXIMUM_VALUE):
                        ok = False
                if ok:
                    self.numberLineEdit.setText(text)
            else:
                if not ok:
                    ok = True

    def startProcess(self):
        connectionRegistry = QgsGPSConnectionRegistry().instance()
        connectionList = connectionRegistry.connectionList()
        if connectionList == []:
            msgBox=QMessageBox(self)
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setWindowTitle(constants.CONST_GNSS_3D_CAPTURE_WINDOW_TITLE)
            msgBox.setText("GPS connection not detected.\nConnect a GPS and try again")
            msgBox.exec_()
            return
        GPSInfo = connectionList[0].currentGPSInformation()
        self.capturePointGroupBox.setEnabled(False)
        if not self.configureDialog.getIsOk():
            msgBox=QMessageBox(self)
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setWindowTitle(constants.CONST_GNSS_3D_CAPTURE_WINDOW_TITLE)
            msgBox.setText("The configuration is not valid")
            msgBox.exec_()
            return
        if self.useCode:
            self.codePushButton.setEnabled(True)
            self.codeLineEdit.setEnabled(True)
        else:
            self.codePushButton.setEnabled(False)
            self.codeLineEdit.setEnabled(False)
            self.codeLineEdit.clear()
        if self.useName:
            self.namePushButton.setEnabled(True)
            self.nameLineEdit.setEnabled(True)
        else:
            self.namePushButton.setEnabled(False)
            self.nameLineEdit.setEnabled(False)
            self.nameLineEdit.clear()
        if self.useNumber:
            self.numberPushButton.setEnabled(True)
            self.numberLineEdit.setEnabled(True)
        else:
            self.numberPushButton.setEnabled(False)
            self.numberLineEdit.setEnabled(False)
            self.numberLineEdit.clear()
        if self.useHeight:
            self.heightAntennaPushButton.setEnabled(True)
            self.heightAntennaLineEdit.setEnabled(True)
            self.antennaHeight = constants.CONST_GNSS_3D_CAPTURE_SAVE_POINT_ANTENNA_HEIGHT_DEFAULT_VALUE
            strAntennaHeigth=constants.CONST_GNSS_3D_CAPTURE_SAVE_POINT_ANTENNA_HEIGHT_PRECISION.format(self.antennaHeight)
            self.heightAntennaLineEdit.setText(strAntennaHeigth)
            self.heightGpsLabel.setEnabled(True)
            self.heightGpsLineEdit.setEnabled(True)
            self.heightGroundLabel.setEnabled(True)
            self.heightGroundLineEdit.setEnabled(True)
            if self.useGeoidModel and self.geoidModelFileName:
                self.heightGeoidLabel.setEnabled(True)
                self.heightGeoidLineEdit.setEnabled(True)
                self.heightFromGeoidLabel.setEnabled(True)
                self.heightFromGeoidLineEdit.setEnabled(True)
            else:
                self.heightGeoidLabel.setEnabled(False)
                self.heightGeoidLineEdit.setEnabled(False)
                self.heightGeoidLineEdit.clear()
                self.heightFromGeoidLabel.setEnabled(False)
                self.heightFromGeoidLineEdit.setEnabled(False)
                self.heightFromGeoidLineEdit.clear()
        else:
            self.heightAntennaPushButton.setEnabled(False)
            self.heightAntennaLineEdit.setEnabled(False)
            self.heightAntennaLineEdit.clear()
            self.heightGpsLabel.setEnabled(False)
            self.heightGpsLineEdit.setEnabled(False)
            self.heightGpsLineEdit.clear()
            self.heightGroundLabel.setEnabled(False)
            self.heightGroundLineEdit.setEnabled(False)
            self.heightGroundLineEdit.clear()
            self.heightGeoidLabel.setEnabled(False)
            self.heightGeoidLineEdit.setEnabled(False)
            self.heightGeoidLineEdit.clear()
            self.heightFromGeoidLabel.setEnabled(False)
            self.heightFromGeoidLineEdit.setEnabled(False)
            self.heightFromGeoidLineEdit.clear()
        fileName = self.csvFileName
        if not fileName:
            msgBox=QMessageBox(self)
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setWindowTitle(constants.CONST_GNSS_3D_CAPTURE_WINDOW_TITLE)
            msgBox.setText("You must select CSV file")
            msgBox.exec_()
            return
        strDateTime=""
        if QFile.exists(fileName):
            msgBox=QMessageBox(self)
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setWindowTitle(constants.CONST_GNSS_3D_CAPTURE_WINDOW_TITLE)
            text="Exists CSV file:\n"+fileName
            msgBox.setText(text)
            msgBox.setInformativeText("Do you want to rename it with current date an time?")
            msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Discard | QMessageBox.Cancel)
            msgBox.setDefaultButton(QMessageBox.Ok)
            ret = msgBox.exec_()
            if ret == QMessageBox.Ok:
                dateTime =QDateTime.currentDateTime()
                strDateTime=dateTime.toString("yyyy-MM-dd_HH-mm-ss")
                fileInfo=QFileInfo(fileName)
                filePath=fileInfo.absolutePath()
                fileNameWithoutExtension=fileInfo.completeBaseName()
                fileExtension=fileInfo.completeSuffix()
                newFileName=filePath+"/"+fileNameWithoutExtension+"_"+strDateTime+"."+fileExtension
                if not QFile.copy(fileName,newFileName):
                    msgBox=QMessageBox(self)
                    msgBox.setIcon(QMessageBox.Warning)
                    msgBox.setWindowTitle(constants.CONST_GNSS_3D_CAPTURE_WINDOW_TITLE)
                    msgBox.setWindowTitle(constants.CONST_GNSS_3D_CAPTURE_WINDOW_TITLE)
                    msgBox.setText("Error copying existing file:\n"+fileName+"\n"+newFileName)
                    msgBox.exec_()
                    return
        if not self.crs.isValid():
            msgBox=QMessageBox(self)
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setWindowTitle(constants.CONST_GNSS_3D_CAPTURE_WINDOW_TITLE)
            msgBox.setText("You must select the output CRS")
            msgBox.exec_()
            return
        if self.useGeoidModel and self.geoidModelFileName == constants.CONST_GNSS_3D_CAPTURE_COMBOBOX_NO_SELECT_OPTION:
            msgBox=QMessageBox(self)
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setWindowTitle(constants.CONST_GNSS_3D_CAPTURE_WINDOW_TITLE)
            msgBox.setText("If you select substract geoide height \n you must select a geoid model")
            msgBox.exec_()
            return
        csvFile=QFile(fileName)
        if not csvFile.open(QIODevice.WriteOnly | QIODevice.Text):
            msgBox=QMessageBox(self)
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setWindowTitle(constants.CONST_GNSS_3D_CAPTURE_WINDOW_TITLE)
            msgBox.setText("Error opening for writting file:\n"+fileName)
            msgBox.exec_()
            return
        csvTextStream = QTextStream(csvFile)
        fileInfo = QFileInfo(fileName)
        self.memoryLayerName = fileInfo.completeBaseName()
        existsMemoryLayer=None
        for lyr in QgsMapLayerRegistry.instance().mapLayers().values():
            if lyr.name() == self.memoryLayerName:
                existsMemoryLayer = lyr
                break
        if existsMemoryLayer != None:
            newMemoryLayerName=self.memoryLayerName+"_"+strDateTime
            existsMemoryLayer.setLayerName(newMemoryLayerName)
        memoryLayerTypeAndCrs="Point?crs=" + self.crs.authid() #EPSG:4326"
        self.memoryLayer = QgsVectorLayer(memoryLayerTypeAndCrs, self.memoryLayerName, "memory")
        self.memoryLayerDataProvider = self.memoryLayer.dataProvider()
        memoryLayerFields=[]
        # add fields
        firstField=True
        if self.useName:
            csvTextStream<<"Name"
            firstField=False
            memoryLayerFields.append(QgsField("Name", QVariant.String))
        if self.useNumber:
            if not firstField:
                csvTextStream<<","
            else:
                firstField=False
            csvTextStream<<"Number"
            memoryLayerFields.append(QgsField("Number", QVariant.Int))
        if not firstField:
            csvTextStream<<","
        else:
            firstField=False
        if not self.crs.geographicFlag():
            csvTextStream<<"Easting"
            csvTextStream<<","<<"Northing"
            memoryLayerFields.append(QgsField("Easting", QVariant.Double))
            memoryLayerFields.append(QgsField("Northing", QVariant.Double))
        else:
            csvTextStream<<"Longitude"
            csvTextStream<<","<<"Latitude"
            memoryLayerFields.append(QgsField("Longitude", QVariant.Double))
            memoryLayerFields.append(QgsField("Latitude", QVariant.Double))
        if self.useHeight:
            csvTextStream<<","<<"Height"
            memoryLayerFields.append(QgsField("Height", QVariant.Double))
        if self.useCode:
            csvTextStream<<","<<"Code"
            memoryLayerFields.append(QgsField("Code", QVariant.String))
        csvFile.close()
        self.memoryLayerDataProvider.addAttributes(memoryLayerFields)
        # self.memoryLayerDataProvider.addAttributes([QgsField("Name", QVariant.String),
        #                                             QgsField("Number", QVariant.String),
        #                                             QgsField("FirstCoordinate", QVariant.Double),
        #                                             QgsField("SecondCoordinate", QVariant.Double),
        #                                             QgsField("Height", QVariant.Double),
        #                                             QgsField("Code",  QVariant.Int)])
        self.memoryLayer.startEditing()
        self.memoryLayer.commitChanges()
        qmlFileName = self.path_plugin + "/" + constants.CONST_GNSS_3D_CAPTURE_QML_TEMPLATES_FOLDER + "/"
        if self.useName:
            qmlFileName += constants.CONST_GNSS_3D_CAPTURE_QML_TEMPLATES_FOLDER_QML_POINT_NAME_Z
        elif self.useNumber:
            qmlFileName += constants.CONST_GNSS_3D_CAPTURE_QML_TEMPLATES_FOLDER_QML_POINT_NUMBER_Z
        else:
            qmlFileName += constants.CONST_GNSS_3D_CAPTURE_QML_TEMPLATES_FOLDER_QML_POINT_Z
        self.memoryLayer.loadNamedStyle(qmlFileName)
        QgsMapLayerRegistry.instance().addMapLayer(self.memoryLayer)
        epsgCodeGps = constants.CONST_GNSS_3D_CAPTURE_EPSG_CODE_GPS
        self.crsGps = QgsCoordinateReferenceSystem(epsgCodeGps)
        if not self.crsGps.isValid():
            msgBox=QMessageBox(self)
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setWindowTitle(constants.CONST_GNSS_3D_CAPTURE_WINDOW_TITLE)
            msgBox.setText("Error creating CRS by EPSG Code: "+str(epsgCodeGps))
            msgBox.exec_()
            self.isValid = False
            return
        self.crsOperationFromGps = QgsCoordinateTransform(self.crsGps,self.crs)
        if self.useHeight:
            if self.useGeoidModel:
                if not QFile.exists(self.geoidModelFileName):
                    msgBox=QMessageBox(self)
                    msgBox.setIcon(QMessageBox.Information)
                    msgBox.setWindowTitle(constants.CONST_GNSS_3D_CAPTURE_WINDOW_TITLE)
                    msgBox.setText("Geoid Model file not exists:\n"+self.geoidModelFileName)
                    msgBox.exec_()
                    self.isValid = False
                    return
                geoidModelFileInfo = QFileInfo(self.geoidModelFileName)
                geoidModelPath = geoidModelFileInfo.filePath()
                geoidModelBaseName = geoidModelFileInfo.baseName()
                self.geoidModel = QgsRasterLayer(geoidModelPath, geoidModelBaseName)
                self.crsGeoidModel = self.geoidModel.crs()
                if not self.crsGeoidModel.isValid():
                    msgBox=QMessageBox(self)
                    msgBox.setIcon(QMessageBox.Information)
                    msgBox.setWindowTitle(constants.CONST_GNSS_3D_CAPTURE_WINDOW_TITLE)
                    msgBox.setText("Error getting Geoid Model CRS:\n"+self.geoidModelFileName)
                    msgBox.exec_()
                    self.isValid = False
                    return
                self.geoidStepFirstCoordinate = self.geoidModel.rasterUnitsPerPixelX()  # debe ser positivo
                self.geoidStepSecondCoordinate = 1.0* self.geoidModel.rasterUnitsPerPixelX()  # debe ser positivo
                self.geoidExtend = self.geoidModel.dataProvider().extent()
                self.geoidMinimumFirstCoordinate = self.geoidExtend.xMinimum()
                self.geoidMaximumSecondCoordinate = self.geoidExtend.yMaximum()
                self.crsOperationFromGpsToGeoid = QgsCoordinateTransform(self.crsGps,self.crsGeoidModel)
        self.capturePointGroupBox.setEnabled(True)
        self.configurePushButton.setEnabled(False)
        self.startPushButton.setEnabled(False)
        self.finishPushButton.setEnabled(True)
        if self.useNumber:
            strFirstNumber = str(constants.CONST_GNSS_3D_CAPTURE_SAVE_POINT_FIRST_POINT_NUMBER)
            self.numberLineEdit.setText(strFirstNumber)
        self.updatePosition()

    def updatePosition(self):
        connectionRegistry = QgsGPSConnectionRegistry().instance()
        connectionList = connectionRegistry.connectionList()
        if connectionList == []:
            msgBox=QMessageBox(self)
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setWindowTitle(constants.CONST_GNSS_3D_CAPTURE_WINDOW_TITLE)
            msgBox.setText("GPS connection not detected.\nConnect a GPS and try again")
            msgBox.exec_()
            return
        GPSInfo = connectionList[0].currentGPSInformation()
        firstCoordinate = GPSInfo.longitude
        secondCoordinate = GPSInfo.latitude
        pointCrsGps = QgsPoint(firstCoordinate,secondCoordinate)
        pointCrs = self.crsOperationFromGps.transform(pointCrsGps)
        firstCoordinate = pointCrs.x()
        secondCoordinate = pointCrs.y()
        if self.crs.geographicFlag():
            strFirstCoordinate = constants.CONST_GNSS_3D_CAPTURE_SAVE_POINT_LONGITUDE_PRECISION.format(firstCoordinate)
            strSecondCoordinate = constants.CONST_GNSS_3D_CAPTURE_SAVE_POINT_LATITUDE_PRECISION.format(secondCoordinate)
        else:
            strFirstCoordinate = constants.CONST_GNSS_3D_CAPTURE_SAVE_POINT_EASTING_PRECISION.format(firstCoordinate)
            strSecondCoordinate = constants.CONST_GNSS_3D_CAPTURE_SAVE_POINT_NORTHING_PRECISION.format(secondCoordinate)
        self.firstCoordinateLineEdit.setText(strFirstCoordinate)
        self.secondCoordinateLineEdit.setText(strSecondCoordinate)
        antennaHeight = float(self.heightAntennaLineEdit.text())
        if self.useHeight:
            height = GPSInfo.elevation
            heightGround = height - antennaHeight
            strHeight=constants.CONST_GNSS_3D_CAPTURE_SAVE_POINT_HEIGHT_PRECISION.format(height)
            self.heightGpsLineEdit.setText(strHeight)
            strHeightGround = constants.CONST_GNSS_3D_CAPTURE_SAVE_POINT_HEIGHT_PRECISION.format(heightGround)
            self.heightGroundLineEdit.setText(strHeightGround)
            if self.useGeoidModel:
                geoidHeight = self.getGeoidInterpolatedValue(GPSInfo.longitude,GPSInfo.latitude)
                if geoidHeight == constants.CONST_GNSS_3D_CAPTURE_GEOIDS_NO_VALUE:
                    return
                strGeoidHeight=constants.CONST_GNSS_3D_CAPTURE_SAVE_POINT_GEOID_HEIGHT_PRECISION.format(geoidHeight)
                heightFromGeoid = heightGround - geoidHeight
                strHeightFromGeoid = constants.CONST_GNSS_3D_CAPTURE_SAVE_POINT_HEIGHT_FROM_GEOID_PRECISION.format(heightFromGeoid)
                self.heightGeoidLineEdit.setText(strGeoidHeight)
                self.heightFromGeoidLineEdit.setText(strHeightFromGeoid)
