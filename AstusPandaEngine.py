
Version = "developer preview"
version = Version

from AGeLib import *

import panda3d as p3d
import panda3d.core as p3dc
from direct.showbase.ShowBase import ShowBase

from direct.showbase.MessengerGlobal import messenger


#import direct.directbase.DirectStart #This import does not import anything but instead starts a ShowBase instance
from direct.showbase.DirectObject import DirectObject
#from pandac.PandaModules import WindowProperties


import sys
import os
import typing
import random

import numpy as np

import _APE_WrapperClasses as Classes

P3D_WIN_WIDTH = 400
P3D_WIN_HEIGHT = 240

#region shortcut functions
def engine():
    return App().engine

def base():
    return App().base
    
def render():
    return App().base.render
    
def loader():
    return App().base.loader

def window():
    return App().MainWindow

def lightManager():
    return App().lightManager

def pipelineActive():
    return App().RenderPipelineActive
#endregion shortcut functions

#region helper functions
def colour(colour: QtGui.QColor) -> typing.Tuple[float,float,float,float]:
    if isinstance(colour, QtGui.QBrush): colour = colour.color()
    try:
        return (colour.redF(), colour.greenF(), colour.blueF(), colour.alphaF())
    except:
        return colour
#endregion helper functions

#region Engine Classes
class APE():
    def __init__(self, base, tobsprRenderPipeline):
        self.RenderPipelineActive = tobsprRenderPipeline
        self.base = base
        App().engine = self

    def start(self):
        """
        This method is called at the end of `start()`. \n
        Reimplement this method with the stuff that starts your game.
        """
        pass

class APEApp(AGeApp):
    def __init__(self, args = [], useExcepthook = True):
        super(APEApp, self).__init__(args,useExcepthook)
        self.base = None #base
        self.engine = None
        self.RenderPipelineActive = False
        self.lightManager = None
        self.installEventFilter(self)

    def eventFilter(self, source, event):
        try:
             # switch control back to qt when the user clicks on the window
            if event.type() == 2 and source.window() == self.MainWindow and self.base.mainWinForeground: self.MainWindow.activateWindow()
        except: pass
        return super(APEApp, self).eventFilter(source, event) # let the normal eventFilter handle the event

    def init_1(self, tobsprRenderPipeline):
        self.RenderPipelineActive = tobsprRenderPipeline
        self.lightManager = Classes._lightManager()

    def init_2(self, base, engine):
        self.base = base
        self.engine = engine

class APEWindow(AWWF):
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
        
        self.lineedit = AGeWidgets.LineEdit(self, PlaceholderText = "Write something and press return to generate a Notification")
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
        wp.setSize(self.width()-self.width()%4, self.height()-self.height()%4)
        wp.setOrigin(0,0)
        base().win.requestProperties(wp)

    def moveEvent(self, evt):
        wp = p3dc.WindowProperties()
        wp.setSize(self.width()-self.width()%4, self.height()-self.height()%4)
        base().win.requestProperties(wp)
	
    def minimumSizeHint(self):
        return QtCore.QSize(400,300)

class APEPandaBase(ShowBase):
    def __init__(self,rp):
        ShowBase.__init__(self)
        self.render_pipeline = rp

    def keystrokeSignal(self, keyname):
        self.MainWindow.S_PandaKeystroke.emit(keyname)
    def buttonDownSignal(self, keyname):
        self.MainWindow.S_PandaButtonDown.emit(keyname)
    def buttonUpSignal(self, keyname):
        self.MainWindow.S_PandaButtonUp.emit(keyname)
    
    def registerWindow(self,window):
        self.MainWindow = window
        self.accept("f11", lambda: self.MainWindow.toggleFullscreen())
        self.accept("f12", lambda: App().makeScreenshot(self.MainWindow))
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

def start(name = "APE Test", engine = APE, base = APEPandaBase, app = APEApp, window = APEWindow, widget = PandaWidget, start = True, tobsprRenderPipeline = True):
    """
    Starts the application using the supplied base classes. If a class is not supplied a standard class is used. \n
    `name`: str -  The name of the application. \n
    `engine`: APE - The Engine class derived from APE. \n
    `base`: APEPandaBase - The Base class derived from APEPandaBase. \n
    `app`: APEApp - The App class derived from APEApp. \n
    `window`: APEWindow - The Window class derived from APEWindow. \n
    `widget`: PandaWidget - The Widget class for the panda3D display derived from PandaWidget. \n
    `start`: bool - If `True` engine.start() is called. Set this to `False` if you want to start the engine later. \n
    `tobsprRenderPipeline`: bool - Set this to `False` if your application is not compatible with tobspr's Render Pipeline. If `True` the user will be asked if they want to use it. \n
    \n
    You do not need to use this function to start your application but it is highly recommended.
    """
    print(AGeAux.cTimeSStr(),": ",name,"Application Startup")
    _app = app(sys.argv)
    _app.ModuleVersions += f"\nAstus Panda Engine {Version}\nPanda3D {p3d.__version__}"
    UseRenderPipeline = QtWidgets.QMessageBox.question(None,"Render Pipeline","Do You want to use tobspr's Render Pipeline?\nThis will make everything look pretty at the cost of performance.") == QtWidgets.QMessageBox.Yes
    if UseRenderPipeline:
        # Insert the pipeline path to the system path, this is required to be
        # able to import the pipeline classes. In case you placed the render
        # pipeline in a subfolder of your project, you have to adjust this.
        sys.path.insert(0, "../tobsprRenderPipeline")
        sys.path.insert(0, "tobsprRenderPipeline")
        # Import render pipeline classes
        from tobsprRenderPipeline import rpcore
        # Construct and create the pipeline
        render_pipeline = rpcore.RenderPipeline()
        render_pipeline.pre_showbase_init()
        Classes._PipelineImport()
    else:
        render_pipeline = False
    _app.init_1(UseRenderPipeline)
    p3dc.loadPrcFileData("", "window-type none")
    _base = base(render_pipeline)
    _engine = engine(_base, render_pipeline)
    _app.init_2(_base,_engine)
    print(AGeAux.cTimeSStr(),": ",name,"Window Startup")
    _window = window(widget)
    _app.setMainWindow(_window)
    _window.setWindowTitle(name)
    _app.setApplicationName(name+"-App")
    _base.registerWindow(_window)
    if UseRenderPipeline:
        render_pipeline.create(_base)
    # this basically creates an idle task
    timer =  QtCore.QTimer(_window)
    timer.timeout.connect( _base.step )
    timer.start(0)
    #
    print(AGeAux.cTimeSStr(),": ",name,"Window Started\n")
    if hasattr(_window,"LastOpenState"):
        _window.LastOpenState()
    else:
        _window.show()
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


#region Laboratory window

class APELabWindow(AWWF):
    S_PandaKeystroke  = pyqtSignal(str)
    S_PandaButtonDown = pyqtSignal(str)
    S_PandaButtonUp   = pyqtSignal(str)
    def __init__(self,widget = PandaWidget):
        super(APELabWindow, self).__init__(IncludeErrorButton=True, FullscreenHidesBars=True)
        App().setMainWindow(self)
        self.LastOpenState = self.showMaximized
        self.CentralSplitter = QtWidgets.QSplitter(self)
        self.setCentralWidget(self.CentralSplitter)
        
        self.TabWidget = QtWidgets.QTabWidget(self.CentralSplitter)
        #
        self.cw = QtWidgets.QWidget(self.CentralSplitter)
        self.pandaContainer = widget(self.cw)
        self.pandaContainer.installEventFilter(self)
        
        self.Console1 = AGeIDE.ConsoleWidget(self)
        self.Console1.setGlobals(self.globals())
        #self.Console1.setText("self.genPlayer()\nself.HexGrid = AGE.HexGrid(self.AGE)\n")
        self.TabWidget.addTab(self.Console1, "Con1")
        self.Console2 = AGeIDE.ConsoleWidget(self)
        self.Console2.setGlobals(self.globals())
        #self.Console2.setText("self.genFloorAndPlayer()\n")
        self.TabWidget.addTab(self.Console2, "Con2")
        #self.GeneratorEditor = AGeIDE.OverloadWidget(self, self.gen, "gen")
        #self.TabWidget.addTab(self.GeneratorEditor, "Gen")
        self.Overload1 = AGeIDE.OverloadWidget(self)
        self.Overload1.setGlobals(self.globals())
        self.TabWidget.addTab(self.Overload1, "Overload 1")
        self.Overload2 = AGeIDE.OverloadWidget(self)
        self.Overload2.setGlobals(self.globals())
        self.TabWidget.addTab(self.Overload2, "Overload 2")
        self.Inspect = AGeIDE.InspectWidget(self)
        self.Inspect.setGlobals(self.globals())
        self.TabWidget.addTab(self.Inspect, "Inspect")
        
        self.setupUI()
        
        self.CentralSplitter.setSizes([App().primaryScreen().size().width(),App().primaryScreen().size().width()])

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
        
        self.cw.setLayout(layout)
        
    def eventFilter(self, source, event):
        #if event.type() == 6: # QtCore.QEvent.KeyPress
        #if hasattr(self,"AGE"):
        #    self.AGE.eventFilter(source, event)
        return super().eventFilter(source, event) # let the normal eventFilter handle the event

    def globals(self):
        return vars(sys.modules['__main__'])

    def gen(self):
        pass

#endregion Laboratory window
