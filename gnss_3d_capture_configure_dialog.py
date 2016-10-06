import os,sys
import shutil
reload(sys)
sys.setdefaultencoding("utf-8")

from PyQt4 import QtCore,QtGui,uic
from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.gui import QgsGenericProjectionSelector
from qgis.core import QgsApplication,QgsCoordinateReferenceSystem

import constants

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'gnss_3d_capture_configure_dialog.ui'))

class GNSS3DCaptureDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self,
                 iface,
                 lastPath,
                 crs,
                 parent=None):
        """Constructor."""
        super(GNSS3DCaptureDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.iface = iface
        self.lastPath=lastPath
        self.crs=crs
        self.initialize()
        self.isOk = False

    def activateGeoid(self):
        if self.geoidCheckBox.isChecked():
            self.geoidLabel.setEnabled(True)
            self.geoidComboBox.setEnabled(True)
            self.geoidComboBox.setCurrentIndex(0)
        else:
            self.geoidLabel.setEnabled(False)
            self.geoidComboBox.setEnabled(False)
            self.geoidComboBox.setCurrentIndex(0)

    def getCrs(self):
        return self.crs

    def getCsvFileName(self):
        return self.csvFileLineEdit.text()

    def getGeoidModelFileName(self):
        geoidModelFileName=""
        if self.geoidCheckBox.isChecked():
            geoidModel=self.geoidComboBox.currentText()
            if geoidModel != constants.CONST_GNSS_3D_CAPTURE_COMBOBOX_NO_SELECT_OPTION:
                geoidModelFileName = self.GeoidsPath + "/" + geoidModel + constants.CONST_GNSS_3D_CAPTURE_GEOIDS_FILE_EXTENSION
        return geoidModelFileName

    def getIsOk(self):
        return self.isOk

    def getLastPath(self):
        return self.lastPath

    def getUseCode(self):
        return self.codeFieldCheckBox.isChecked()

    def getUseGeoidModel(self):
        return self.geoidCheckBox.isChecked()

    def getUseHeight(self):
        return self.heightFieldCheckBox.isChecked()

    def getUseName(self):
        return self.nameFieldCheckBox.isChecked()

    def getUseNumber(self):
        return self.numberFieldCheckBox.isChecked()

    def initialize(self):
        crsAuthId=self.crs.authid()
        self.crsLineEdit.setText(crsAuthId)
        self.initializeGeoidComboBox()
        QtCore.QObject.connect(self.csvFilePushButton,QtCore.SIGNAL("clicked(bool)"),self.selectCsvFile)
        QtCore.QObject.connect(self.crsPushButton,QtCore.SIGNAL("clicked(bool)"),self.selectCrs)
        QtCore.QObject.connect(self.geoidCheckBox,QtCore.SIGNAL("clicked(bool)"),self.activateGeoid)
        self.buttonBox.accepted.connect(self.selectAccept)

    def initializeGeoidComboBox(self):
        self.geoidComboBox.addItem(constants.CONST_GNSS_3D_CAPTURE_COMBOBOX_NO_SELECT_OPTION)
        qgisAppPath=QgsApplication.prefixPath()
        qgisDir=QDir(qgisAppPath)
        qgisDir.cdUp()
        qgisDir.cdUp()
        qgisPath=qgisDir.absolutePath()
        shareDir=QDir(qgisPath + constants.CONST_GNSS_3D_CAPTURE_GEOIDS_RELATIVE_PATH)
        self.GeoidsPath = qgisPath+constants.CONST_GNSS_3D_CAPTURE_GEOIDS_RELATIVE_PATH
        geoidFileNames = shareDir.entryList([constants.CONST_GNSS_3D_CAPTURE_GEOIDS_FILTER_1], QtCore.QDir.Files) #,QtCore.QDir.Name)
        for geoidFileName in geoidFileNames:
            geoidFileInfo=QFileInfo(geoidFileName)
            self.geoidComboBox.addItem(geoidFileInfo.baseName())

    def selectAccept(self):
        if self.crsLineEdit.text():
            if self.csvFileLineEdit.text():
                self.isOk = True
        self.close()

    def selectCrs(self):
        projSelector = QgsGenericProjectionSelector()
        ret = projSelector.exec_()
        if ret == 1: #QMessageBox.Ok:
            crsId=projSelector.selectedCrsId()
            crsAuthId=projSelector.selectedAuthId()
            self.crsLineEdit.setText(self.crsAuthId)
            self.crs.createFromUserInput(self.crsAuthId)

    def selectCsvFile(self):
        oldFileName=self.csvFileLineEdit.text()
        title="Select CSV file"
        filters="Files (*.csv)"
        fileName = QFileDialog.getSaveFileName(self,title,self.lastPath,filters)
        if fileName:
            fileInfo = QFileInfo(fileName)
            self.lastPath=fileInfo.absolutePath()
            self.csvFileLineEdit.setText(fileName)
