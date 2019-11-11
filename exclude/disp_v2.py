# -*- coding: utf-8 -*-
"""
Created on Tue May 22 16:41:20 2018

@author: controlroom
"""


import pyqtgraph as pq
import PyTango as pt
import time
import sys
import numpy as np
from PyQt4 import QtGui, QtCore # (the example applies equally well to PySide)
from time import sleep
#import matplotlib.pyplot as plt
import scipy.misc as scpym


class TangoDeviceClient(QtGui.QWidget):
    def __init__(self, parent = None):
        QtGui.QWidget.__init__(self, parent)
        
        
        #horn antenna osciloscope devices
        self.horn2device = pt.DeviceProxy('I-C080008/DIA/OSCA-01')
        self.horn1device = pt.DeviceProxy('I-KBC1/DIA/OSCA-01')
        #print self.horn2device.read_attribute('Waveform4').value
        
        #B_I_LinacLS01_Open_C
        #I-B080603/PSS/PLC-01/B_I_LinacLS01_Close_C
        self.shutterDevice = pt.DeviceProxy('I-B080603/PSS/PLC-01')

        
        # pull device attribute names from the Tango database
        db = pt.Database()
        # Export every magnet there is
        self.magnetlist = db.get_device_exported_for_class('Magnet')[:]
#        print type(self.magnetlist)
        cameralist = db.get_device_exported_for_class('LiveViewer')[:] 
        BPMlist = db.get_device_exported_for_class('LiberaSinglePassE')[:] 
        screenlist = db.get_device_exported_for_class('CameraScreen')[:] 
        self.cameraNames = [x for x in cameralist if ('/I-' in x or '/i-' in x)]  
        
        self.BPMNames = [x for x in BPMlist if 'BPL' in x]
        self.screenNames = [x for x in screenlist if 'SCRN' in x]
        
        self.stop_timer = False
        self.cameraTimer = QtCore.QTimer()
        self.cameraTimer.timeout.connect(self.updateImage)
        self.oscTimer = QtCore.QTimer()
        self.oscTimer.timeout.connect(self.updateHornTrace)
                
        self.screenSelected = 'none'
        self.imgAxisSelected = 0
        
        self.stdTrend = np.array([])
        self.horn1Trend = np.array([])
        self.horn2Trend = np.array([])


        
        self.myLayout()
        self.updateHornTrace()
    
    def fwhm(self,data):
        data = np.abs(data)
        data /= np.max(data)
        a = [np.diff(np.sign(data-0.5))]
        nonzeros = np.nonzero(a[0])
        fwhm = np.max(nonzeros)-np.min(nonzeros)
        #print np.min(nonzeros), np.max(nonzeros)
        return fwhm           
        
    def updateHornTrace(self):
        self.horn1trace = self.horn1device.read_attribute('Waveform4').value
        self.horn1trace = -self.horn1trace + np.mean(self.horn1trace[-9:])
        self.horn2trace = self.horn2device.read_attribute('Waveform4').value
        self.horn2trace = self.horn2trace - np.mean(self.horn2trace[-9:])
        
        self.plot11.setData(self.horn1trace)
        self.plot21.setData(self.horn2trace)
        self.plot21.setPen('r')   

        
        horn1trace_current = np.sum(self.horn1trace)
        self.horn1Trend = np.append(self.horn1Trend,horn1trace_current)
        self.plot31.setData(self.horn1Trend[-49:])
        
        horn2trace_current = np.sum(self.horn2trace)
        self.horn2Trend = np.append(self.horn2Trend,horn2trace_current)
        self.plot41.setData(self.horn2Trend[-49:])
        self.plot41.setPen('r')   
        
        if self.stop_timer is not True:
            self.oscTimer.start(450)
        print 'updating horn antenna'

    def updateImage(self):
        #print 'updating image'
        if self.subtractBkgndButton.isChecked():
            self.image = self.cameraDevice.read_attribute('Image').value.astype(np.double)-self.bkgndImage
        else:
            self.image = self.cameraDevice.read_attribute('Image').value.astype(np.double)
        self.img.setImage(self.image) #[425:525,500:600]

        #self.plot11.setData(np.sum(self.image,axis=0),title='x lineout')
        #self.plot21.setData(np.sum(self.image,axis=1))
        self.view.update()
        #std_current = np.std(np.sum(self.image,axis=self.imgAxisSelected))
        self.imgLineout = np.sum(self.image,axis=0)
        fwhm_current = self.fwhm(self.imgLineout)
        self.stdTrend = np.append(self.stdTrend,fwhm_current)
        self.plot51.setData(self.imgLineout)
        self.plot61.setData(self.stdTrend[-49:])
        if self.stop_timer is not True:
            self.cameraTimer.start(400)
        print 'image updated'
           
 
    def myLayout(self):        
        self.layout = QtGui.QHBoxLayout(self) #the whole window, main layout
        self.leftLayout = QtGui.QVBoxLayout()
        self.middleLayout = QtGui.QVBoxLayout()
        self.rightLayout = QtGui.QVBoxLayout()
        self.controlsLayout = QtGui.QGridLayout()
        self.lineoutsLayout = QtGui.QGridLayout()
        self.cameraLayout = QtGui.QVBoxLayout()
        self.plotLayout = QtGui.QVBoxLayout()
        
        self.layout.addLayout(self.leftLayout)
        self.layout.addLayout(self.middleLayout)
        self.layout.addLayout(self.rightLayout)
        self.middleLayout.addLayout(self.controlsLayout)
        self.leftLayout.addLayout(self.lineoutsLayout)
        self.leftLayout.addLayout(self.cameraLayout)
        self.rightLayout.addLayout(self.plotLayout)

                      
        self.plotWidget1 = pq.PlotWidget(title='BC1 horn antenna')
        self.plotWidget1.setVisible(True)
        self.plotWidget1.setMaximumSize(350,170)
        self.plot11 = self.plotWidget1.plot()

        self.plotWidget2 = pq.PlotWidget(title='BC2 horn antenna')
        self.plotWidget2.setVisible(True)
        self.plotWidget2.setMaximumSize(350,170)
        self.plot21 = self.plotWidget2.plot(axisItems = ['signal sum','pixel','',''])
    

        self.lineoutsLayout.addWidget(self.plotWidget1)
        self.lineoutsLayout.addWidget(self.plotWidget2)
        
            
        self.cameraWindow = pq.GraphicsLayoutWidget()
        self.cameraWindow.setMaximumSize(350,350)
        #self.cameraWindow.setSizePolicy(QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Expanding)
        self.cameraLayout.addWidget(self.cameraWindow)
        self.view = self.cameraWindow.addViewBox()
        self.view.setAspectLocked(True)
        self.img = pq.ImageItem(border='w')
        self.view.addItem(self.img)

        
        self.chooseScreenBox = QtGui.QComboBox()
        self.chooseScreenBox.addItems(self.cameraNames)
        self.screenSelectedLabel = QtGui.QLabel("none selected")
        self.screenBoxLabel = QtGui.QLabel("select camera")     
        self.cameraStartButton = QtGui.QPushButton("start camera")
        self.cameraStopButton = QtGui.QPushButton("stop camera")
        self.saveImagesButton = QtGui.QPushButton("save images")
        self.noImagesBox = QtGui.QSpinBox()
        self.noImagesBox.setValue(5)
        self.imageNameBox = QtGui.QLineEdit()
        self.imageFolderNameBox = QtGui.QLineEdit()

        
        
        self.VExpSpacer=QtGui.QSpacerItem(100,100,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Expanding)
        self.VFixSpacer=QtGui.QSpacerItem(100,100,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.VFixSmallSpacer=QtGui.QSpacerItem(100,25,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
   

        self.controlsLayout.addWidget(self.screenBoxLabel,8,0)
        self.controlsLayout.addWidget(self.chooseScreenBox,9,0)    
        self.controlsLayout.addWidget(self.screenSelectedLabel,10,0)
        self.controlsLayout.addWidget(self.cameraStartButton,11,0)
        self.controlsLayout.addWidget(self.cameraStopButton,12,0)
        self.controlsLayout.addItem(self.VExpSpacer,13,0)
        self.controlsLayout.addWidget(self.saveImagesButton,14,0)
        self.controlsLayout.addWidget(self.noImagesBox,15,0)
        self.controlsLayout.addWidget(QtGui.QLabel("file name"),16,0)
        self.controlsLayout.addWidget(self.imageNameBox,17,0)
        self.controlsLayout.addWidget(QtGui.QLabel("folder name"),18,0)
        self.controlsLayout.addWidget(self.imageFolderNameBox,19,0)
        self.controlsLayout.addItem(self.VExpSpacer,20,0)
        
        
        self.saveBkgndButton = QtGui.QPushButton('Save Background')
        self.saveBkgndButton.clicked.connect(self.saveBkgnd) 
        self.subtractBkgndButton = QtGui.QRadioButton()
        self.subtractBkgndButton.setText('Subtract bkgnd')
 
        self.controlsLayout.addWidget(self.saveBkgndButton,21,0)
        self.controlsLayout.addWidget(self.subtractBkgndButton,22,0)
        

        self.chooseScreenBox.activated.connect(self.updatescreenSelected)
        self.cameraStartButton.clicked.connect(self.cameraStart)
        self.cameraStopButton.clicked.connect(self.cameraStop)    
        self.saveImagesButton.clicked.connect(self.saveImages)
        
        self.rightLayout.addLayout(self.plotLayout)
        
        self.plotWidget3 = pq.PlotWidget(title='BC1 horn antenna trend')
        self.plotWidget3.setVisible(True)
        self.plotWidget3.setMaximumSize(350,185)
        self.plot31 = self.plotWidget3.plot()
 
        self.plotWidget4 = pq.PlotWidget(title='BC2 horn antenna trend')
        self.plotWidget4.setVisible(True)
        self.plotWidget4.setMaximumSize(350,185)
        self.plot41 = self.plotWidget4.plot()
        
        self.plotWidget5 = pq.PlotWidget(title='beam lineout')
        self.plotWidget5.setVisible(True)
        self.plotWidget5.setMaximumSize(350,185)
        self.plot51 = self.plotWidget5.plot()
        
        self.plotWidget6 = pq.PlotWidget(title='beam treans. std trend')
        self.plotWidget6.setVisible(True)
        self.plotWidget6.setMaximumSize(350,185)
        self.plot61 = self.plotWidget6.plot()        
        
        self.plotLayout.addWidget(self.plotWidget3)
        self.plotLayout.addWidget(self.plotWidget4)
        self.plotLayout.addWidget(self.plotWidget5)
        self.plotLayout.addWidget(self.plotWidget6)

        
    def saveImages(self):
        for i in range(1,self.noImagesBox.value()+1):
            if self.subtractBkgndButton.isChecked():
                self.image = self.cameraDevice.read_attribute('Image').value.astype(np.double)-self.bkgndImage
            else:
                self.image = self.cameraDevice.read_attribute('Image').value.astype(np.double)
            self.img.setImage(self.image) #[425:525,500:600]
            imgname = str(self.imageNameBox.text())
            imgfoldername = str(self.imageFolderNameBox.text())
            filename = ''.join((imgfoldername,'/',imgname,'img',str(i), time.strftime('%Y-%m-%d_%Hh%M'), '.tiff'))
            scpym.imsave(filename,self.image)
            sleep(1)
            
        

    def startScan(self):
        self.noCorrScanPoints = self.corrScanPointsButton.value()
        self.corrScanRange = self.corrScanRangeButton.value()
        self.corrScanValues = np.linspace(self.corrCurrent-self.corrScanRange/2,self.corrCurrent+self.corrScanRange/2,self.noCorrScanPoints)
        
        self.noQuadScanPoints = self.quadScanPointsButton.value()
        self.quadScanRange = self.quadScanRangeButton.value()
        self.quadScanValues = np.linspace(self.quadCurrent-self.quadScanRange/2,self.quadCurrent+self.ScanRange/2,self.noCorrScanPoints)
                
    def findPeakPosition(self):
        print 'finding peak position̈́'
        if ('X' in str(self.corrSelected)):
            current_axis = 0
        else:
            current_axis = 1
        self.lineoutCurrent = np.sum(self.image,axis=current_axis)
        maxindex = np.where(self.lineoutCurrent == np.max(self.lineoutCurrent))[0]
        print maxindex
        self.findPeakLabel.setText(str(maxindex)) 

    def cameraStop(self):
        self.cameraDevice.stop()
        
    def cameraStart(self):
         self.cameraDevice.start()
         sleep(2)
         self.cameraDevice.startacquisition()      
        
    def saveBkgnd(self):
        #self.shutterDevice.write_attribute('B_I_LinacLS01_Close_C',True)
        #print 'closed shutter'
        sleep(1)
        self.bkgndImage = self.cameraDevice.read_attribute('Image').value.astype(np.double)
        #self.shutterDevice.write_attribute('B_I_LinacLS01_Open_C',True)
        #print 'opened shutter'

    
    def subtractBkgnd(self):
        pass
              

    def updatescreenSelected(self):
        self.screenSelected = self.chooseScreenBox.currentText()
        self.screenSelectedLabel.setText(self.screenSelected)
        #print type(self.screenSelected)
        self.cameraDevice = pt.DeviceProxy(str(self.screenSelected))
        #self.cameraDevice.set_timeout_millis(3000)
        
        #take one image to determine the size of self.bkgndImage
        self.image = self.cameraDevice.read_attribute('Image').value.astype(np.double) 
        self.bkgndImage = np.zeros((len(self.image),1))        
                
        self.updateImage()
        
    def closeEvent(self, event):
        self.stop_timer = True
        self.deleteLater()
        time.sleep(0.1)
        print 'stopping'


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    myapp = TangoDeviceClient()
    myapp.show()
    sys.exit(app.exec_())
    

