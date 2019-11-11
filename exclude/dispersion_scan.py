# -*- coding: utf-8 -*-
"""
Created on Tue May 22 16:12:41 2018

@author: controlroom
"""


import pyqtgraph as pq
import PyTango as pt
#import time
import sys
import numpy as np
from PyQt4 import QtGui, QtCore # (the example applies equally well to PySide)
from time import sleep
#import matplotlib.pyplot as plt
#from scipy import misc


class TangoDeviceClient(QtGui.QWidget):
    def __init__(self, parent = None):
        QtGui.QWidget.__init__(self, parent)
        
        
        
        # pull device attribute names from the Tango database
        db = pt.Database()
        
        #horn antenna osciloscope devices
        self.horn2device = pt.DeviceProxy('i-c080008/dia/osca-01')
        self.horn1device = pt.DeviceProxy('i-kbc1/dia/osca-01')
 
        cameralist = db.get_device_exported_for_class('LiveViewer')[:] 
        BPMlist = db.get_device_exported_for_class('LiberaSinglePassE')[:] 
        screenlist = db.get_device_exported_for_class('CameraScreen')[:] 
        self.cameraNames = [x for x in cameralist if ('/I-' in x or '/i-' in x)]  
        
        self.BPMNames = [x for x in BPMlist if 'BPL' in x]
        self.screenNames = [x for x in screenlist if 'SCRN' in x]
        
        self.scanTimer = QtCore.QTimer()
        self.scanTimer.timeout.connect(self.updateImage)
                
        self.quadSelected = 'none'
        self.corrSelected = 'none'
        self.screenSelected = 'none'
        
        self.myLayout()
    
    def updateNamesLists(self):
        pass
        
        
    def fwhm(self,data):
        data = np.abs(data)
        data /= np.max(data)
        a = [np.diff(np.sign(data-0.5))]
        nonzeros = np.nonzero(a[0])
        fwhm = np.max(nonzeros)-np.min(nonzeros)
        #print np.min(nonzeros), np.max(nonzeros)
        return fwhm     

    def updateImage(self):
        #print 'updating image'
        if self.subtractBkgndButton.isChecked():
            self.image = self.cameraDevice.read_attribute('Image').value.astype(np.double)-self.bkgndImage
        else:
            self.image = self.cameraDevice.read_attribute('Image').value.astype(np.double)
        self.img.setImage(self.image) #[425:525,500:600]
        self.horn1trace = self.horn1device.read_attribute_('Waveform4').value
        self.plot11.setData(self.horn1trace)
        #self.plot11.setData(np.sum(self.image,axis=0),title='x lineout')
        #self.plot21.setData(np.sum(self.image,axis=1))
        self.plot21.setPen('r')   
        self.view.update()
        #self.cameraWindow.update()
        self.scanTimer.start(100)
        
    def scanQuad(self):
        pass
        #self.quadSelectedPowerSupplyProxy.write_attribute('Current',)
               
 
    def myLayout(self):        
        self.layout = QtGui.QHBoxLayout(self) #the whole window, main layout
        self.leftLayout = QtGui.QVBoxLayout()
        self.middleLayout = QtGui.QVBoxLayout()
        self.rightLayout = QtGui.QVBoxLayout()
        self.controlsLayout = QtGui.QGridLayout()
        self.lineoutsLayout = QtGui.QGridLayout()
        self.cameraLayout = QtGui.QVBoxLayout()
        self.scanLayout = QtGui.QGridLayout()
        
        #sizeConstraint = QtGui.QLayout.sizeConstraint([200,200])
        #self.middleLayout.setSizeConstraint(sizeConstraint)
        
        self.layout.addLayout(self.leftLayout)
        self.layout.addLayout(self.middleLayout)
        self.layout.addLayout(self.rightLayout)
        self.middleLayout.addLayout(self.controlsLayout)
        self.leftLayout.addLayout(self.lineoutsLayout)
        self.leftLayout.addLayout(self.cameraLayout)
        self.rightLayout.addLayout(self.scanLayout)

                      
        self.plotWidget1 = pq.PlotWidget(title='x lineout')
        self.plotWidget1.setVisible(True)
        self.plotWidget1.setMaximumSize(350,170)
        self.plot11 = self.plotWidget1.plot()
#        self.plot11.setData(np.sum(self.image,axis=0),pen='w',name='x lineout')

        self.plotWidget2 = pq.PlotWidget(title='y lineout')
        self.plotWidget2.setVisible(True)
        self.plotWidget2.setMaximumSize(350,170)
        self.plot21 = self.plotWidget2.plot(axisItems = ['signal sum','pixel','',''])
#        self.plot21.setData(np.sum(self.image,axis=0),pen='w',name='y lineout')    
    

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
        #self.img.setImage(self.image)
        
        #self.startButton = QtGui.QPushButton('Subtract background')
        #self.startButton.clicked.connect(self.subtractBackground)

#        self.chooseQuadBox = QtGui.QComboBox()
#        self.chooseQuadBox.addItems(self.quadNames)
#        self.quadSelectedLabel = QtGui.QLabel("none selected")
#        self.quadBoxLabel = QtGui.QLabel("select quad")
#        self.quadCurrentLabel = QtGui.QLabel("---")
#        
#    
#        self.chooseCorrBox = QtGui.QComboBox()
#        self.chooseCorrBox.addItems(self.corrNames)
#        self.corrSelectedLabel = QtGui.QLabel("none selected")
#        self.corrBoxLabel = QtGui.QLabel("select corrector")
#        self.corrCurrentLabel = QtGui.QLabel("---")
        
        self.chooseScreenBox = QtGui.QComboBox()
        self.chooseScreenBox.addItems(self.cameraNames)
        self.screenSelectedLabel = QtGui.QLabel("none selected")
        self.screenBoxLabel = QtGui.QLabel("select screen")     
        self.cameraStartButton = QtGui.QPushButton("start camera")
        
        self.VExpSpacer=QtGui.QSpacerItem(100,100,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Expanding)
        self.VFixSpacer=QtGui.QSpacerItem(100,100,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.VFixSmallSpacer=QtGui.QSpacerItem(100,25,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)


    
#        self.controlsLayout.addWidget(self.quadBoxLabel,0,0)
#        self.controlsLayout.addWidget(self.chooseQuadBox,1,0)    
#        self.controlsLayout.addWidget(self.quadSelectedLabel,2,0)
#        self.controlsLayout.addWidget(self.quadCurrentLabel,2,1)
#        self.controlsLayout.addItem(self.VFixSpacer,3,0)
#        self.controlsLayout.addWidget(self.corrBoxLabel,4,0)
#        self.controlsLayout.addWidget(self.chooseCorrBox,5,0)    
#        self.controlsLayout.addWidget(self.corrSelectedLabel,6,0)
#        self.controlsLayout.addWidget(self.corrCurrentLabel,6,1)
#        self.controlsLayout.addItem(self.VFixSpacer,7,0)
        self.controlsLayout.addWidget(self.screenBoxLabel,0,0)
        self.controlsLayout.addWidget(self.chooseScreenBox,1,0)    
        self.controlsLayout.addWidget(self.screenSelectedLabel,2,0)
        self.controlsLayout.addWidget(self.cameraStartButton,3,0)
        self.controlsLayout.addItem(self.VExpSpacer,4,0)
        
#        self.chooseQuadBox.activated.connect(self.updateQuadSelected)
#        self.chooseCorrBox.activated.connect(self.updateCorrSelected)
        self.chooseScreenBox.activated.connect(self.updatescreenSelected)
        self.cameraStartButton.clicked.connect(self.cameraStart)
        
        self.saveBkgndButton = QtGui.QPushButton('Save Background')
        self.saveBkgndButton.clicked.connect(self.saveBkgnd) 
        self.subtractBkgndButton = QtGui.QRadioButton()
        self.subtractBkgndButton.setText('Subtract bkgnd')
 
        self.controlsLayout.addWidget(self.saveBkgndButton,5,0)
        self.controlsLayout.addWidget(self.subtractBkgndButton,6,0)
              
 
        
#        self.quadScanRangeButtonLabel = QtGui.QLabel('quad scan range')
#        self.quadScanRangeButton = QtGui.QSpinBox()
#        self.scanLayout.addWidget(self.quadScanRangeButtonLabel)
#        self.scanLayout.addWidget(self.quadScanRangeButton)
#        self.scanLayout.addItem(self.VFixSmallSpacer)
#        
#        self.quadScanPointsButtonLabel = QtGui.QLabel('# corr scan points')
#        self.quadScanPointsButton = QtGui.QSpinBox()
#        self.scanLayout.addWidget(self.quadScanPointsButtonLabel)
#        self.scanLayout.addWidget(self.quadScanPointsButton)
#        self.scanLayout.addItem(self.VFixSpacer)
#        
#        self.shotsToAvgButtonLabel = QtGui.QLabel('# shots to avg.')
#        self.shotsToAvgButton = QtGui.QSpinBox()
#        self.scanLayout.addWidget(self.shotsToAvgButtonLabel)
#        self.scanLayout.addWidget(self.shotsToAvgButton)
#        self.scanLayout.addItem(self.VFixSpacer)
#        
#        self.startScanButton = QtGui.QPushButton('Start scan')
#        self.scanLayout.addWidget(self.startScanButton)
#        self.startScanButton.clicked.connect(self.startScan)
#        
#        self.scanLayout.addItem(self.VExpSpacer)

 
        
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


        
    def cameraStart(self):
         self.cameraDevice.start()
         sleep(2)
         self.cameraDevice.startacquisition()      
        
    def saveBkgnd(self):
        self.bkgndImage = self.cameraDevice.read_attribute('Image').value.astype(np.double)
    
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


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    myapp = TangoDeviceClient()
    myapp.show()
    sys.exit(app.exec_())
    

