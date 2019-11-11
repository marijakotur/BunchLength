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
#from scipy.stats import norm 
from scipy.optimize import curve_fit


class TangoDeviceClient(QtGui.QWidget):
    def __init__(self, parent = None):
        QtGui.QWidget.__init__(self, parent)
        
        
        #horn antenna osciloscope devices
        self.horn2device = pt.DeviceProxy('I-C080008/DIA/OSCA-01')
        self.horn1device = pt.DeviceProxy('I-KBC1/DIA/OSCA-01')
        #print self.horn2device.read_attribute('Waveform4').value
        
        self.sexDev = pt.DeviceProxy('I-KBC1/MAG/PSPA-01')
        sexCurrent = self.sexDev.read_attribute('Current').value
        #print sexCurrent
        
        #B_I_LinacLS01_Open_C
        #I-B080603/PSS/PLC-01/B_I_LinacLS01_Close_C
        self.shutterDevice = pt.DeviceProxy('I-B080603/PSS/PLC-01')
        
        self.K01fillDevice = pt.DeviceProxy('I-K01/RF/DLY-01')
        
        self.L00PhaseDevice = pt.DeviceProxy('i-k00/rf/phs-02')
        self.L01PhaseDevice = pt.DeviceProxy('i-k01/rf/phs-01')
        self.L02PhaseDevice = pt.DeviceProxy('i-k02/rf/phs-01')
        self.L00Phase = self.L00PhaseDevice.read_attribute('PhaseDifference').value
        self.L01Phase = self.L01PhaseDevice.read_attribute('PhaseDifference').value
        self.L02Phase = self.L02PhaseDevice.read_attribute('PhaseDifference').value
        
        self.BPM_BC1_dev = pt.DeviceProxy('i-bc1/dia/bpl-01')
        self.BPM_BC2_dev = pt.DeviceProxy('i-bc2/dia/bpl-01')
        #print self.BPM_BC1_dev.read_attribute('Sum').value
        #print self.BPM_BC2_dev.read_attribute('Sum').value
        
        self.BC1SextupolDevice = pt.DeviceProxy('I-BC1/MAG/CRSX-01')
        self.BC2SextupolDevice = pt.DeviceProxy('I-BC2/MAG/CRSX-01')
        
        self.BC2QuadDevice = pt.DeviceProxy('I-KBC2/MAG/PSPG-01-CAB07')
        self.BC1QuadDevice = pt.DeviceProxy('I-KBC1/MAG/PSPB-06')

        
        self.BC1DipoleDevice = pt.DeviceProxy('I-KBC1/MAG/PSCC-01')
        self.BC2DipoleDevice = pt.DeviceProxy('I-KBC2/MAG/PSCC-01')
        
        
        self.settings_dictionary = {
            "screen":'',
            "L00crest":0.0,
            "L00phase":self.L00Phase,
            "L01crest":0.0,
            "L01phase":self.L01Phase,
            "L02crest":0.0,
            "L02phase":self.L02Phase,
            "charge_BC1":0.0,
            "charge_BC2":0.0,
            "sext_BC1_k2":0.0,
            "sext_BC2_k2":0.0,
            "quad_BC1":0.0,
            "quad_BC2":0.0,
            "dip_BC1":0.0,
            "dip_BC2":0.0
            }
        
        #roi initial values
        self._pixX = 300
        self._pixY = 120
        
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
        

        
    def saveSettings(self,settings_filename):
        
        self.settings_dictionary['L00phase']=self.L00Phase   
        self.settings_dictionary['L01phase']=self.L01Phase   
        self.settings_dictionary['L02phase']=self.L02Phase   
        
        self.settings_dictionary['L00crest']=float(self.L00PhaseCrest.text())
        self.settings_dictionary['L01crest']=float(self.L01PhaseCrest.text())
        self.settings_dictionary['L02crest']=float(self.L02PhaseCrest.text())

        
        self.settings_dictionary['charge_BC1']=self.BPM_BC1_dev.read_attribute('Sum').value
        self.settings_dictionary['charge_BC2']=self.BPM_BC2_dev.read_attribute('Sum').value
        
        self.settings_dictionary['sext_BC1_k2']= self.BC1SextupolDevice.read_attribute('MainFieldComponent').value
        self.settings_dictionary['sext_BC2_k2']=self.BC2SextupolDevice.read_attribute('MainFieldComponent').value
        
        self.settings_dictionary['quad_BC1']=self.BC1QuadDevice.read_attribute('Current').value
        self.settings_dictionary['quad_BC2']=self.BC2QuadDevice.read_attribute('Current').value
        
        self.settings_dictionary['dip_BC1']=self.BC1DipoleDevice.read_attribute('Current').value
        self.settings_dictionary['dip_BC2']=self.BC2DipoleDevice.read_attribute('Current').value
        
        self.settings_dictionary['screen']=str(self.chooseScreenBox.currentText())

        sleep(0.2)
        
        f = open(settings_filename,"w")
        f.write(str(self.settings_dictionary))
        f.close()
            
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
        self.L00PhaseRead.setText(str(self.L00PhaseDevice.read_attribute('PhaseDifference').value))
        self.L01PhaseRead.setText(str(self.L01PhaseDevice.read_attribute('PhaseDifference').value))
        self.L02PhaseRead.setText(str(self.L02PhaseDevice.read_attribute('PhaseDifference').value))

        # print self.L00PhaseDevice.read_attribute('PhaseDifference').value     
        

    def updateImage(self):
        #print 'updating image'
        if self.subtractBkgndButton.isChecked():
            #self.image = self.cameraDevice.read_attribute('Image').value.astype(np.double)-self.bkgndImage
            self.image = np.rot90(self.cameraDevice.image.astype(np.int16)-self.bkgndImage,3)
        else:
            self.image = np.rot90(self.cameraDevice.image,3).astype(np.int16)
            #self.image = self.cameraDevice.read_attribute('Image').value.astype(np.double)
        self.img.setImage(self.image) #[425:525,500:600]

        #self.plot11.setData(np.sum(self.image,axis=0),title='x lineout')
        #self.plot21.setData(np.sum(self.image,axis=1))
        #self.view.update()
        #std_current = np.std(np.sum(self.image,axis=self.imgAxisSelected))
        crop = self._roi.getArrayRegion(self.image,self.img)
        #print np.shape(crop)
        self.imgLineout = np.sum(crop,axis=1)
        #fwhm_current = self.fwhm(self.imgLineout)
        #fwhm_current = 0
 
        
        #lineout and fit to it
        self.plot51.setData(self.imgLineout)
        #print len(self.imgLineout)
        
        
        if self.stop_timer is not True:
            self.cameraTimer.start(400)
        # print 'image updated'
            
        #fitting        
        ydata = self.imgLineout
        xdata = np.arange(1, len(ydata)+1)
        #initial guess for the fit
        c = np.mean(ydata[0:25] + ydata[-26:-1]) / 2
        mu = len(xdata)/2
        s = 50
        a = np.max(ydata) - c 
        p0 =    [c, a, mu, s]  
            #coeff, var_matrix = curve_fit(self.gaus_func, xdata, ydata, p0=p0)
        #fit = self.gaus_func(xdata, *coeff)    
        #print coeff    
        
        #self.plot52.setData(fit)
        
        #try:
        #    self.stdTrend = np.append(self.stdTrend,coeff[3])
        #except Exception as e:
        #    self._output.setText(str(e))
        #self.plot61.setData(self.stdTrend[-49:])

        
            
    def gaus_func(self, x, *p):
        """Function for fitting a Gaussian profile"""
        C, A, mu, sigma = p
        return A * np.exp( -(x-mu)**2 / (2.*sigma**2) ) + C

            
    def change_roi(self):
        x, y = self._roi.size()
        self._pixX = np.round(x)
        self._pixY = np.round(y)        
               
 
    def myLayout(self):        
        self.layout = QtGui.QHBoxLayout(self) #the whole window, main layout
        self.leftLayout = QtGui.QVBoxLayout()
        self.middleLayout = QtGui.QVBoxLayout()
        self.rightLayout = QtGui.QHBoxLayout()
        self.controlsLayout = QtGui.QGridLayout()
        self.lineoutsLayout = QtGui.QGridLayout()
        self.cameraLayout = QtGui.QVBoxLayout()
        self.plotLayout = QtGui.QVBoxLayout()
        self.phaseLayout = QtGui.QVBoxLayout()
        
        self.layout.addLayout(self.leftLayout)
        self.layout.addLayout(self.middleLayout)
        self.layout.addLayout(self.rightLayout)
        self.middleLayout.addLayout(self.controlsLayout)
        self.leftLayout.addLayout(self.lineoutsLayout)
        self.leftLayout.addLayout(self.cameraLayout)
        self.rightLayout.addLayout(self.plotLayout)
        self.rightLayout.addLayout(self.phaseLayout)

                      
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
        
        
        #camera image
        #self.cameraWindow = pq.GraphicsLayoutWidget()
        self.cameraWindow = pq.PlotWidget()
        self.cameraWindow.setMaximumSize(350,350)
        #self.cameraWindow.setSizePolicy(QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Expanding)
        self.cameraLayout.addWidget(self.cameraWindow)
        #self.view = self.cameraWindow.addViewBox()
        #self.view.setAspectLocked(True)
        self.img = pq.ImageItem(border='w')
        self.cameraWindow.addItem(self.img)

        #roi
        self._roi = pq.ROI([300, 440], [self._pixX, self._pixY])
        self._roi.addScaleHandle(1, 0)
        self._roi.scaleSnap = True  # Force ROI to integer snap positions
        #self._roi.maxBounds = QtCore.QRect(0, 0, 1280, 1024)
        self._roi.sigRegionChangeFinished.connect(self.change_roi)
        self.cameraWindow.addItem(self._roi)
        self._roi.setZValue(10)  # make sure ROI is drawn above image
        
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
        self.plot52 = self.plotWidget5.plot()
        pen=pq.mkPen('r', width=2, style=QtCore.Qt.DashLine)
        self.plot52.setPen(pen)
        
        self.plotWidget6 = pq.PlotWidget(title='beam treans. std trend')
        self.plotWidget6.setVisible(True)
        self.plotWidget6.setMaximumSize(350,185)
        self.plot61 = self.plotWidget6.plot()        
        
        self.plotLayout.addWidget(self.plotWidget3)
        self.plotLayout.addWidget(self.plotWidget4)
        self.plotLayout.addWidget(self.plotWidget5)
        self.plotLayout.addWidget(self.plotWidget6)
        
        #phases
        self.L00PhaseCrest = QtGui.QLineEdit()
        self.L00PhaseCrest.setText('1000')
        self.L00PhaseWrite = QtGui.QDoubleSpinBox()
        self.L00PhaseWrite.setRange(0,1000)
        self.L00PhaseWrite.setDecimals(1)
        self.L00PhaseRead = QtGui.QLabel()
        
        self.L01PhaseCrest = QtGui.QLineEdit()
        self.L01PhaseCrest.setText('303')
        self.L01PhaseWrite = QtGui.QDoubleSpinBox()
        self.L01PhaseWrite.setRange(0,1000)
        self.L01PhaseWrite.setDecimals(1)
        self.L01PhaseRead = QtGui.QLabel()     
        
        self.L02PhaseCrest = QtGui.QLineEdit()
        self.L02PhaseCrest.setText('163')
        self.L02PhaseWrite = QtGui.QDoubleSpinBox()
        self.L02PhaseWrite.setDecimals(1)
        self.L02PhaseWrite.setRange(0,1000)
        self.L02PhaseRead = QtGui.QLabel()  
        
        self.phaseLayout.addWidget(QtGui.QLabel("L00 crest phase"))
        self.phaseLayout.addWidget(self.L00PhaseCrest)
        self.phaseLayout.addWidget(QtGui.QLabel("L00 phase"))
        self.phaseLayout.addWidget(self.L00PhaseWrite)
        L00Phase =self.L00PhaseDevice.read_attribute('PhaseDifference').value
        self.L00PhaseWrite.setValue(L00Phase)
        self.L00PhaseWrite.valueChanged.connect(self.setL00Phase)
        self.phaseLayout.addWidget(self.L00PhaseRead)
        self.L00PhaseDevice.read_attribute('PhaseDifference').value
        self.L00PhaseRead.setText(str(self.L00PhaseDevice.read_attribute('PhaseDifference').value))

        
        self.phaseLayout.addItem(self.VFixSpacer) 
        
        self.phaseLayout.addWidget(QtGui.QLabel("L01 crest phase"))
        self.phaseLayout.addWidget(self.L01PhaseCrest)
        self.phaseLayout.addWidget(QtGui.QLabel("L01 phase"))   
        self.phaseLayout.addWidget(self.L01PhaseWrite)
        L01Phase =self.L01PhaseDevice.read_attribute('PhaseDifference').value
        self.L01PhaseWrite.setValue(L01Phase)
        self.L01PhaseWrite.valueChanged.connect(self.setL01Phase)
        self.phaseLayout.addWidget(self.L01PhaseRead)  
        self.L01PhaseDevice.read_attribute('PhaseDifference').value
        self.L01PhaseRead.setText(str(self.L01PhaseDevice.read_attribute('PhaseDifference').value))
        
        
        self.phaseLayout.addItem(self.VFixSpacer)
        
        self.phaseLayout.addWidget(QtGui.QLabel("L02 crest phase"))
        self.phaseLayout.addWidget(self.L02PhaseCrest)
        self.phaseLayout.addWidget(QtGui.QLabel("L02 phase"))   
        self.phaseLayout.addWidget(self.L02PhaseWrite)
        L02Phase =self.L02PhaseDevice.read_attribute('PhaseDifference').value
        self.L02PhaseWrite.setValue(L02Phase)
        self.L02PhaseWrite.valueChanged.connect(self.setL02Phase)
        self.phaseLayout.addWidget(self.L02PhaseRead)  
        self.L02PhaseDevice.read_attribute('PhaseDifference').value
        self.L02PhaseRead.setText(str(self.L02PhaseDevice.read_attribute('PhaseDifference').value))        
        
        
        self.phaseLayout.addItem(self.VExpSpacer)
                
        
    def setL00Phase(self):
        L00Phase = self.L00PhaseWrite.value()
        print 'changing L00 phase to', L00Phase
        self.L00PhaseDevice.write_attribute('PhaseDifference',L00Phase)
        
    def setL01Phase(self):
        L01Phase = self.L01PhaseWrite.value()
        self.L01PhaseDevice.write_attribute('PhaseDifference',L01Phase)
        
    def setL02Phase(self):
        L02Phase = self.L02PhaseWrite.value()
        self.L02PhaseDevice.write_attribute('PhaseDifference',L02Phase)

        
    def saveImages(self):
        #self.imgfoldername = str(self.imageFolderNameBox.text())
        self.imgfoldername  = '/home/controlroom/Desktop/Link to linac/Measurements/190423_Sextupolescan_streak/Tessa scan 2'
        #self.imgfoldername  = 'test'
        imgname = str(self.imageNameBox.text())
        self.horn1TraceStacked = []
        horn1filename = ''.join((self.imgfoldername,'/',imgname,'_','horn1','_', time.strftime('%Y-%m-%d_%Hh%M'), '.txt'))
        sex_min = 0 #4.12
        sex_max = 9.6
        sex_steps = 168 #120
        for sex_current in np.linspace(sex_min,sex_max,sex_steps):
            self.sexDev.write_attribute('Current',sex_current)
            sleep(2)
            
            for i in range(self.noImagesBox.value()):
                if self.subtractBkgndButton.isChecked():
                    image = self.cameraDevice.read_attribute('Image').value.astype(np.double)-self.bkgndImage
                else:
                    image = self.cameraDevice.read_attribute('Image').value.astype(np.double)
                #self.img.setImage(self.image) #[425:525,500:600]
                horn1trace = self.horn1device.read_attribute('Waveform4').value
                horn1trace = -horn1trace + np.mean(horn1trace[-9:])
                filename = ''.join((self.imgfoldername,'/',imgname,'_sex',str(sex_current),'_img',str(i+1),'_', time.strftime('%Y-%m-%d_%Hh%M'), '.tiff'))
                scpym.imsave(filename,image)
                self.horn1TraceStacked.append(horn1trace)
                #if i==1:
                    #print 'saving settings'
                    #settings_filename = ''.join((self.imgfoldername,'/',imgname,'settings','.txt'))
                    #self.saveSettings(settings_filename)
                sleep(1)
            
        np.savetxt(horn1filename,self.horn1TraceStacked)
        #f = open(horn1filename,"a+")
        #f.write(self.horn1trace)
        #f.close()

         
#        with open(horn1filename,"w") as f:
#            for line in self.horn1TraceStacked:
#                np.savetxt(f,line,fmt='%.6f')
        #f.close()            

                
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
        self.shutterDevice.write_attribute('B_I_LinacLS01_Close_C',True)
        print 'closed shutter'
        sleep(1)
        self.bkgndImage = self.cameraDevice.read_attribute('Image').value.astype(np.int16)
        self.shutterDevice.write_attribute('B_I_LinacLS01_Open_C',True)
        print 'opened shutter'
              

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
        self.stop_timer = Truecam
        self.deleteLater()
        time.sleep(0.1)
        print 'stopping'


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    myapp = TangoDeviceClient()
    myapp.show()
    sys.exit(app.exec_())
    
