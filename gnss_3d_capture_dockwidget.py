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

from gnss_3d_capture_configure_dialog import *

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

    def initialize(self):
        aux_path_plugin = 'python/plugins/' + constants.CONST_GPS_3D_CAPTURE_PLUGIN_NAME
        qgisUserDbFilePath = QgsApplication.qgisUserDbFilePath()
        self.path_plugin = os.path.join(QFileInfo(QgsApplication.qgisUserDbFilePath()).path(),aux_path_plugin)
        path_file_qsettings = self.path_plugin + '/' +constants.CONST_GPS_3D_CAPTURE_SETTINGS_FILE_NAME
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
        # QtCore.QObject.connect(self.finishPushButton,QtCore.SIGNAL("clicked(bool)"),self.finishProcess)
        # QtCore.QObject.connect(self.savePointPushButton,QtCore.SIGNAL("clicked(bool)"),self.savePoint)
        self.pointNumbers = []
        self.configureDialog = None

    def selectConfigure(self):
        if self.configureDialog == None:
            self.configureDialog = GNSS3DCaptureDialog(self.iface,self.lastPath,self.crs)
            self.configureDialog.show() # show the dialog
            result = self.configureDialog.show().exec_() # Run the dialog
        else:
            self.configureDialog.show() # show the dialog
#        if self.configureDialog.isOk():
        self.csvFileName=self.configureDialog.getCsvFileName()
        self.lastPath = self.configureDialog.getLastPath()
        self.crs = self.configureDialog.getCrs()
        self.useCode = self.configureDialog.getUseCode()
        self.useName = self.configureDialog.getUseName()
        self.useHeigth = self.configureDialog.getUseHeight()
        self.useNumber = self.configureDialog.getUseNumber()
        self.useGeoidModel = self.configureDialog.getUseGeoidModel()
        self.geoidFileName = self.configureDialog.getGeoidModelFileName()
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

    def startProcess(self):
        self.capturePointGroupBox.isEnabled(False)
        if not self.configureDialog.isOk():
            msgBox=QMessageBox(self)
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setWindowTitle(constants.CONST_GPS_3D_CAPTURE_PLUGIN_WINDOW_TITLE)
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
            self.heightAntennaLineEdit.setText(constants.CONST_GPS_3D_CAPTURE_PLUGIN_SAVE_POINT_ANTENNA_HEIGHT_DEFAULT_VALUE)
            self.heightGpsLabel.setEnabled(True)
            self.heightGpsLineEdit.setEnabled(True)
            self.heightGroundLabel.setEnabled(True)
            self.heightGroundLineEdit.setEnabled(True)
            if self.useGeoidModel and self.geoidFileName:
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
            msgBox.setWindowTitle(constants.CONST_GPS_3D_CAPTURE_PLUGIN_WINDOW_TITLE)
            msgBox.setText("You must select CSV file")
            msgBox.exec_()
            return
        if QFile.exists(fileName):
            msgBox=QMessageBox(self)
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setWindowTitle(constants.CONST_GPS_3D_CAPTURE_PLUGIN_WINDOW_TITLE)
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
                    msgBox.setWindowTitle(constants.CONST_GPS_3D_CAPTURE_PLUGIN_WINDOW_TITLE)
                    msgBox.setWindowTitle(constants.CONST_GPS_3D_CAPTURE_PLUGIN_WINDOW_TITLE)
                    msgBox.setText("Error copying existing file:\n"+fileName+"\n"+newFileName)
                    msgBox.exec_()
                    return
        if not self.crs.isValid():
            msgBox=QMessageBox(self)
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setWindowTitle(constants.CONST_GPS_3D_CAPTURE_PLUGIN_WINDOW_TITLE)
            msgBox.setText("You must select the output CRS")
            msgBox.exec_()
            return
        self.capturePointGroupBox.isEnabled(True)

        if applyGeoid and geoidModel == constants.CONST_GPS_3D_CAPTURE_PLUGIN_COMBOBOX_NO_SELECT_OPTION:
            msgBox=QMessageBox(self)
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setWindowTitle(constants.CONST_GPS_3D_CAPTURE_PLUGIN_WINDOW_TITLE)
            msgBox.setText("If you select substract geoide height \n you must select a geoid model")
            msgBox.exec_()
            return
        csvFile=QFile(fileName)
        if not csvFile.open(QIODevice.WriteOnly | QIODevice.Text):
            msgBox=QMessageBox(self)
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setWindowTitle(constants.CONST_GPS_3D_CAPTURE_PLUGIN_WINDOW_TITLE)
            msgBox.setText("Error opening for writting file:\n"+fileName)
            msgBox.exec_()
            return
        csvTextStream = QTextStream(csvFile)
        firstField=True
        if self.nameFieldCheckBox.isChecked():
            csvTextStream<<"Name"
            firstField=False
        if self.numberFieldCheckBox.isChecked():
            if not firstField:
                csvTextStream<<","
            else:
                firstField=False
            csvTextStream<<"Number"
        if not firstField:
            csvTextStream<<","
        else:
            firstField=False
        csvTextStream<<"Easting"
        csvTextStream<<","<<"Northing"
        if self.heightFieldCheckBox.isChecked():
            csvTextStream<<","<<"Height"
        if self.codeFieldCheckBox.isChecked():
            csvTextStream<<","<<"Code"
        csvFile.close()
        self.savePointPushButton.setEnabled(True)
        self.finishPushButton.setEnabled(True)
        self.csvFilePushButton.setEnabled(False)
        self.crsPushButton.setEnabled(False)
        self.geoidCheckBox.setEnabled(False)
        self.geoidComboBox.setEnabled(False)
        self.fieldsGroupBox.setEnabled(False)
        self.startPushButton.setEnabled(False)
