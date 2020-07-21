
Version = "developer preview"
version = Version

import AGeLib as age
from AGeLib import NC

import panda3d as p3d
import panda3d.core as p3dc
from direct.showbase.ShowBase import ShowBase

from direct.showbase.MessengerGlobal import messenger

#import direct.directbase.DirectStart #This import does not import anything but instead starts a ShowBase instance
from direct.showbase.DirectObject import DirectObject
#from pandac.PandaModules import WindowProperties

from PyQt5.QtCore import pyqtProperty, pyqtSignal # pylint: disable=no-name-in-module
from PyQt5 import QtWidgets,QtCore,QtGui,Qt
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView,QWebEngineSettings # pylint: disable=no-name-in-module
except:
    from PyQtWebEngine.QtWebEngineWidgets import QWebEngineView,QWebEngineSettings


import sys

P3D_WIN_WIDTH = 400
P3D_WIN_HEIGHT = 240

#region shortcut functions
def engine():
    return age.App().engine

def base():
    return age.App().base
    
def render():
    return age.App().base.render
    
def loader():
    return age.App().base.loader

def window():
    return age.App().MainWindow
#endregion shortcut functions

#region Engine Classes
class APE():
    def __init__(self, base):
        self.base = base
        age.App().engine = self

    def start(self):
        """
        This method is called at the end of `start()`. \n
        Reimplement this method with the stuff that starts your game.
        """
        pass

class APEApp(age.MainApp):
    def __init__(self, base, args = []):
        super(APEApp, self).__init__(args)
        self.base = base
        self.engine = None
        self.installEventFilter(self)

    def eventFilter(self, source, event):
        try:
             # switch control back to qt when the user clicks on the window
            if event.type() == 2 and source.window() == self.MainWindow and self.base.mainWinForeground: self.MainWindow.activateWindow()
        except: pass
        return super(APEApp, self).eventFilter(source, event) # let the normal eventFilter handle the event

    def init(self, base, engine, window):
        self.base = base
        self.engine = engine
        self.setMainWindow(window)

class APEWindow(age.AWWF):
    S_PandaKeystroke  = pyqtSignal(str)
    S_PandaButtonDown = pyqtSignal(str)
    S_PandaButtonUp   = pyqtSignal(str)
    def __init__(self, widget, parent=None):
        super(APEWindow, self).__init__(parent, initTopBar=False, FullscreenHidesBars=True)
        self.TopBar.init(IncludeFontSpinBox=True,IncludeErrorButton=True)
        self.setWindowTitle("Test")
        
        self.cw = QtWidgets.QWidget(self)
        self.pandaContainer = widget(self.cw)
        self.setupUI()
        self.setCentralWidget(self.cw)

    def setupUI(self):
        """
        This Method sets up the UI. \n
        If you want a different layout reimplement this Method. \n
        All you need to do is to create a layout and apply it to `self.cw`.\n
        `self.cw` is automatically set as the Central Widget. \n
        `self.pandaContainer` is the Panda3D Widget and is created automatically.
        """
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.pandaContainer)
        
        self.lineedit = age.LineEdit(self, PlaceholderText = "Write something and press return to generate a Notification")
        def sendMessage():
            NC(3,self.lineedit.text(),DplStr="LineEdit Input")
            self.lineedit.clear()
        self.lineedit.returnPressed.connect(sendMessage)
        layout.addWidget(self.lineedit)
        
        self.cw.setLayout(layout)

class PandaWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(PandaWidget, self).__init__(parent)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))

    def resizeEvent(self, evt):
        wp = p3dc.WindowProperties()
        wp.setSize(self.width(), self.height())
        wp.setOrigin(0,0)
        base().win.requestProperties(wp)

    def moveEvent(self, evt):
        wp = p3dc.WindowProperties()
        wp.setSize(self.width(), self.height())
        base().win.requestProperties(wp)
	
    def minimumSizeHint(self):
        return QtCore.QSize(400,300)

class APEPandaBase(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

    def keystrokeSignal(self, keyname):
        self.MainWindow.S_PandaKeystroke.emit(keyname)
    def buttonDownSignal(self, keyname):
        self.MainWindow.S_PandaButtonDown.emit(keyname)
    def buttonUpSignal(self, keyname):
        self.MainWindow.S_PandaButtonUp.emit(keyname)
    
    def registerWindow(self,window):
        self.MainWindow = window
        self.accept("f11", self.MainWindow.toggleFullscreen)
        wp = p3dc.WindowProperties()
        wp.setOrigin(0,0)
        wp.setSize(P3D_WIN_WIDTH, P3D_WIN_HEIGHT)
        wp.set_parent_window(int(self.MainWindow.pandaContainer.winId()))
        #wp.
        self.openDefaultWindow(props=wp)
        
    def step(self):
        self.taskMgr.step()
        
    def windowEvent(self, win):
        if win != self.win:
            # This event isn't about our window.
            return

        properties = win.getProperties()
        if properties != self._ShowBase__prevWindowProperties: # pylint: disable=access-member-before-definition
            self._ShowBase__prevWindowProperties = properties # pylint: disable=access-member-before-definition

            self.notify.debug("Got window event: %s" % (repr(properties)))
            if not properties.getOpen():
                # If the user closes the main window, we should exit.
                self.notify.info("User closed main window.")
                self.userExit()

            if properties.getForeground() and not self.mainWinForeground:
                self.mainWinForeground = 1
            elif not properties.getForeground() and self.mainWinForeground:
                self.mainWinForeground = 0

            if properties.getMinimized() and not self.mainWinMinimized:
                # If the main window is minimized, throw an event to
                # stop the music.
                self.mainWinMinimized = 1
                messenger.send('PandaPaused')
            elif not properties.getMinimized() and self.mainWinMinimized:
                # If the main window is restored, throw an event to
                # restart the music.
                self.mainWinMinimized = 0
                messenger.send('PandaRestarted')

            # If we have not forced the aspect ratio, let's see if it has
            # changed and update the camera lenses and aspect2d parameters
            self.adjustWindowAspectRatio(self.getAspectRatio())

            if win.hasSize() and win.getSbsLeftYSize() != 0:
                self.pixel2d.setScale(2.0 / win.getSbsLeftXSize(), 1.0, 2.0 / win.getSbsLeftYSize())
                if self.wantRender2dp:
                    self.pixel2dp.setScale(2.0 / win.getSbsLeftXSize(), 1.0, 2.0 / win.getSbsLeftYSize())
            else:
                xsize, ysize = self.getSize()
                if xsize > 0 and ysize > 0:
                    self.pixel2d.setScale(2.0 / xsize, 1.0, 2.0 / ysize)
                    if self.wantRender2dp:
                        self.pixel2dp.setScale(2.0 / xsize, 1.0, 2.0 / ysize)

    
#class World(DirectObject):   
 #    def __init__(self):
 #        self.accept("a", self.pressedA)
 #        self.accept("escape", sys.exit)
 #        #
 #    
 #    def pressedA(self):
 #        print("a pressed, keyboard focus ok")
 #        #self.cam = base.makeCamera(self)#.buff
 #        #self.camNode = self.cam.node()
 #        #self.camLens = self.camNode.get_lens()
 #        #self.cam.setPos(0, -28, 6)
 #        ##self.win.setClearColorActive(True)
 #        ##self.win.setClearColor(p3dc.VBase4(0, 0.5, 0, 1))        
 #        #self.testModel = loader.loadModel('panda')
 #        #self.testModel.reparentTo(render)
 #        #
 #        ## This rotates the actor 180 degrees on heading and 90 degrees on pitch.
 #        #myInterval4 = self.testModel.hprInterval(1.0, p3dc.Vec3(360, 0, 0))
 #        #myInterval4.loop()

#endregion Engine Classes

#region Main Functions

def start(name = "APE Test", engine = APE, base = APEPandaBase, app = APEApp, window = APEWindow, widget = PandaWidget, start = True):
    print(age.cTimeSStr(),": ",name,"Window Startup")
    p3dc.loadPrcFileData("", "window-type none")
    _base = base()
    _app = app(_base, sys.argv)
    _app.ModuleVersions += f"\nAstus Panda Engine {Version}\nPanda3D {p3d.__version__}"
    _engine = engine(_base)
    _window = window(widget)
    _app.setMainWindow(_window)
    _window.setWindowTitle(name)
    _app.setApplicationName(name+"-App")
    _base.registerWindow(_window)
    # this basically creates an idle task
    timer =  QtCore.QTimer(_window)
    timer.timeout.connect( _base.step )
    timer.start(0)
    #
    print(age.cTimeSStr(),": ",name,"Window Started\n")
    _window.show()
    _window.positionReset()
    if start:
        _engine.start()
    _base.buttonThrowers[0].node().setKeystrokeEvent('keystroke')
    _base.buttonThrowers[0].node().setButtonDownEvent('buttonDown')
    _base.buttonThrowers[0].node().setButtonUpEvent('buttonUp')
    _base.accept('keystroke', _base.keystrokeSignal)
    _base.accept('buttonDown', _base.buttonDownSignal)
    _base.accept('buttonUp', _base.buttonUpSignal)
    _app.exec_()

#endregion Main Functions

#region Main Classes
class APEScene():
    def __init__(self):
        self._models = {}

    def addModel(self, model, name):
        self._models[name] = model
        return model
        
class APEObject():
    def __init__(self):
        pass


#endregion Main Classes

