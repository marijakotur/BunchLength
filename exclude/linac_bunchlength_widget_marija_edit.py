import sys
sys.dont_write_bytecode = True
from time import sleep

import numpy as np
from scipy.optimize import curve_fit
from savitzky_golay import savitzky_golay
import logging
logging.basicConfig(format='%(asctime)s :: %(message)s', level=logging.INFO)

import PyTango as PT
from PyQt4 import QtCore, QtGui
import pyqtgraph as pq
pq.setConfigOptions(antialias=True)


class CustomViewBox(pq.ViewBox):
    def __init__(self, *args, **kwds):
        pq.ViewBox.__init__(self, *args, **kwds)
        self.setMouseMode(self.RectMode)
        
    ## reimplement right-click to zoom out
    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.RightButton:
            self.enableAutoRange('xy', True)
            
    def mouseDragEvent(self, ev):
        if ev.button() == QtCore.Qt.RightButton:
            ev.ignore()
        else:
            pq.ViewBox.mouseDragEvent(self, ev)


class LinacBunchLengthWidget(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        
        
        self.dispersion = 0.32 
        #self.dispersion = 0.53
        
        """Static attributes"""
        # Camera to pull data from
        self._cam = PT.DeviceProxy('lima/liveviewer/i-bc2-dia-scrn-01')
        
        # mm per pixel on camera
        self._mm_pix = 0.02396989381337041
        
        """User attributes"""
        # Number of pixels to average over
        self._pixX = 600
        self._pixY = 120
        
        # Degrees off crest in main linac
        self._mainphase = 35
        self.change_main_phase(self._mainphase)
        
        # Smoothing parameters
        self._smoothwindow = 7
        self._smoothorder = 2
        
        """Setup plots, labels, and layout"""
        self._plotImg = pq.PlotWidget(title='Raw image data')
        self._viewImg = pq.ImageItem()
        self._plotImg.addItem(self._viewImg)
        
        self._roi = pq.ROI([300, 440], [self._pixX, self._pixY])
        self._roi.addScaleHandle(1, 0)
        self._roi.scaleSnap = True  # Force ROI to integer snap positions
        #self._roi.maxBounds = QtCore.QRect(0, 0, 1280, 1024)
        self._roi.sigRegionChangeFinished.connect(self.change_roi)
        self._plotImg.addItem(self._roi)
        self._roi.setZValue(10)  # make sure ROI is drawn above image
        
        l1 = pq.InfiniteLine(angle=0, movable=False, pen='b')
        self._plotImg.addItem(l1)
        l2 = pq.InfiniteLine(angle=90, movable=False, pen='b')
        self._plotImg.addItem(l2)
        l3 = pq.InfiniteLine(angle=0, movable=False, pen='b')
        l3.setValue(1024)
        self._plotImg.addItem(l3)
        l4 = pq.InfiniteLine(angle=90, movable=False, pen='b')
        l4.setValue(1280)
        self._plotImg.addItem(l4)
        
        vb = CustomViewBox()
        self._plotTrace = pq.PlotWidget(viewBox=vb, title='Trace and fit')
        self._plotTrace.setLabel('left', 'Intensity', units=None)
        self._plotTrace.setLabel('bottom', 'Pixel', units=None)
        
        self._curveRaw = self._plotTrace.plot(pen=pq.mkPen('g', width=2, style=QtCore.Qt.SolidLine))
        self._curveFit = self._plotTrace.plot(pen=pq.mkPen('r', width=3, style=QtCore.Qt.DashLine))

        layout = QtGui.QGridLayout()
        layout.setSpacing(8)
        layout.addWidget(self._plotImg, 0, 0)
        layout.addWidget(self._plotTrace, 0, 1)

        sublayout1 = QtGui.QGridLayout()
        
        sublayout1.addWidget(QtGui.QLabel('Degrees off crest:'), 0, 0)
        sublayout1.addWidget(self.build_editfield(str(self._mainphase), 50, False, self.change_main_phase), 0, 1)
        
        sublayout1.addWidget(QtGui.QLabel('Smoothing window: [odd integer > order]'), 1, 0)
        sublayout1.addWidget(self.build_editfield(str(self._smoothwindow), 50, False, self.change_smooth_window), 1, 1)
        
        sublayout1.addWidget(QtGui.QLabel('Smoothing order: [nth polynomial, 0 to disable]'), 2, 0)
        sublayout1.addWidget(self.build_editfield(str(self._smoothorder), 50, False, self.change_smooth_order), 2, 1)
        
        button_start = QtGui.QPushButton('Start')
        button_start.setMinimumWidth(100)
        button_start.setMaximumWidth(100)
        button_start.clicked.connect(self.start)
        sublayout1.addWidget(button_start, 3, 0)
        button_stop = QtGui.QPushButton('Stop')
        button_stop.setMinimumWidth(100)
        button_stop.setMaximumWidth(100)
        button_stop.clicked.connect(self.stop)
        sublayout1.addWidget(button_stop, 3, 1)
        button_stop = QtGui.QPushButton('Save new background')
        button_stop.clicked.connect(self.save_bckg)
        sublayout1.addWidget(button_stop, 0, 2)
        
        self._output = QtGui.QLabel('')
        sublayout1.addWidget(self._output, 4, 0, 1, 3)
        
        sublayout2 = QtGui.QGridLayout()
        
        sublayout2.addWidget(QtGui.QLabel('FWHM (fit)'), 0, 0)
        self.lab_fwhm_fit = self.build_editfield('', 125, True, None)
        sublayout2.addWidget(self.lab_fwhm_fit, 0, 1)

        sublayout2.addWidget(QtGui.QLabel('FWHM (data)'), 1, 0)
        self.lab_fwhm_data = self.build_editfield('', 125, True, None)
        sublayout2.addWidget(self.lab_fwhm_data, 1, 1)
        
        sublayout2.addWidget(QtGui.QLabel('Bunch length (FWHM fit)'), 2, 0)
        self.lab_bl_fwhm_fit = self.build_editfield('', 125, True, None)
        sublayout2.addWidget(self.lab_bl_fwhm_fit, 2, 1)
        
        sublayout2.addWidget(QtGui.QLabel('Bunch length (FWHM data)'), 3, 0)
        self.lab_bl_fwhm_data = self.build_editfield('', 125, True, None)
        sublayout2.addWidget(self.lab_bl_fwhm_data, 3, 1)
        
        sublayout2.addWidget(QtGui.QLabel('Bunch length (sigma fit)'), 4, 0)
        self.lab_bl_sigma_fit = self.build_editfield('', 125, True, None)
        sublayout2.addWidget(self.lab_bl_sigma_fit, 4, 1)
        
        sublayout2.addWidget(QtGui.QLabel('Bunch length (sigma data'), 5, 0)
        self.lab_bl_sigma_data = self.build_editfield('', 125, True, None)
        sublayout2.addWidget(self.lab_bl_sigma_data, 5, 1)
        
        layout.addLayout(sublayout1, 1, 0)
        layout.addLayout(sublayout2, 1, 1)
        
        self.setLayout(layout)
        self.setWindowTitle('Linac bunch length widget')
        
        # Load background image
        try:
            dire = '/mxn/groups/operators/controlroom/python_programs/qtw-linac-bunch-length-widget'
            self._bckg = np.load(dire + '/i-bc2-dia-scrn-01_background.npy').astype(np.int16)
        except Exception as e:
            self._bckg = 0
            logging.error('No background file loaded. ' + str(e))
            self._output.setText(str(e))
        
        """Start update timer"""
        self._running = False
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(1000)
        
        
    def build_editfield(self, text, length, readflag, func):
        ed = QtGui.QLineEdit(text)
        ed.setMaximumWidth(length)
        ed.setReadOnly(readflag)
        if func is not None:
            ed.textChanged.connect(func)
        return ed
        
    def change_main_phase(self, val):
        # Conversion factor for bunch length
        try:
            self._C = self.dispersion * np.sin(float(val)*np.pi / 180.) * 2. * np.pi * 3e9;
        except Exception as e:
            self._output.setText(str(e))
        
    def change_smooth_window(self, val):
        try:
            self._smoothwindow = int(val)
        except Exception as e:
            self._output.setText(str(e))
        
    def change_smooth_order(self, val):
        try:
            self._smoothorder = int(val)
        except Exception as e:
            self._output.setText(str(e))
        
    def change_roi(self):
        x, y = self._roi.size()
        self._pixX = np.round(x)
        self._pixY = np.round(y)
    
    def start(self):
        self._running = True
        logging.info('Starting...')
        
    def stop(self):
        self._running = False
        logging.info('Stopping...')
        
    def save_bckg(self):
        img = np.rot90(self._cam.image, 3)
        for i in range(1,10):
            img += np.rot90(self._cam.image, 3)
            sleep(1)
        imgAvg = img/10

        dire = '/mxn/groups/operators/controlroom/python_programs/qtw-linac-bunch-length-widget'
        np.save(dire + '/i-bc2-dia-scrn-01_background.npy', imgAvg)
        logging.info('Saved background image.')
        self._bckg = imgAvg
    
    def update(self):
        if self._running:
            try:
                img = np.rot90(self._cam.image, 3).astype(np.int16) - self._bckg
                self._viewImg.setImage(img)

                """Construct x and y arrays"""
                crop = self._roi.getArrayRegion(img, self._viewImg)
                horMax, verMax = np.unravel_index(crop.argmax(), crop.shape)
                arr = np.mean(crop, axis=1)

                reg = [self._roi.pos()[0], self._roi.pos()[0] + self._roi.size()[0]]
                xf = np.arange(reg[0], reg[1])
                
                """Smooth the signal"""
                if self._smoothorder != 0:
                    arr = savitzky_golay(arr, self._smoothwindow, self._smoothorder)
                
                """Initial guess for fit parameters"""
                off = np.mean(arr[0:25] + arr[-26:-1]) / 2
                c = xf[-1] - (xf[-1] - xf[0])/2
                s = 50
                p0 = [off, np.max(arr), c, s]
        
                coeff, var_matrix = curve_fit(self.gaus, xf, arr, p0=p0)
                fit = self.gaus(xf, *coeff)
                
                self._curveRaw.setData(arr)
                self._curveFit.setData(fit)
                
                # FWHM = 2 * sqrt( 2 * log(2) ) * sigma
                fwhm_f = 2.3548 * coeff[3]
                fwhm_d = len(arr[arr > np.max(arr)/2])
                
                self.lab_fwhm_fit.setText(str( format(fwhm_f, '.4f') ) + ' px')
                self.lab_fwhm_data.setText(str( fwhm_d ) + ' px')
                self.lab_bl_fwhm_fit.setText(str( format( (1e12 * self._mm_pix * fwhm_f * 1e-3) / self._C , '.4f') ) + ' ps')
                self.lab_bl_fwhm_data.setText(str( format( (1e12 * self._mm_pix * fwhm_d * 1e-3) / self._C , '.4f') ) + ' ps')
                self.lab_bl_sigma_fit.setText(str( format( (1e12 * self._mm_pix * coeff[3] * 1e-3) / self._C , '.4f') ) + ' ps')
                self.lab_bl_sigma_data.setText(str( format(  np.std(arr)  , '.4f') ) + ' px')

                self._output.setText('')

            except Exception as e:
                logging.error('Error somewhere! ' + str(e))
                self._output.setText(str(e))
        
        
    def gaus(self, x, *p):
        """Function for fitting a Gaussian profile"""
        C, A, mu, sigma = p
        return C + A * np.exp( -(x-mu)**2 / (2.*sigma**2) )
        
    def closeEvent(self, event):
        self._running = False
        self.timer.stop()
        logging.info('Closed widget')
        
        
        
def main():
    app = QtGui.QApplication(sys.argv)
    bunchWid = LinacBunchLengthWidget()
    bunchWid.show()
    sys.exit(app.exec_())
        
if __name__ == "__main__":
    main() 
