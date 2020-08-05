import datetime
import platform
WindowTitle = "APE-Test"
if __name__ == "__main__":
    print()
    print(datetime.datetime.now().strftime('%H:%M:%S'))
    print(WindowTitle)
    print("Loading Modules")#,end="")
    if platform.system() == 'Windows':
        try:
            import ctypes
            myAppId = u'{}{}'.format(WindowTitle , datetime.datetime.now().strftime('%H:%M:%S')) # arbitrary string
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myAppId)
        except:
            pass

import AGeLib as age

import panda3d as p3d
import panda3d.core as p3dc
from direct.showbase.ShowBase import ShowBase


#import direct.directbase.DirectStart #This import does not import anything but instead starts a ShowBase instance
from direct.showbase.DirectObject import DirectObject
#from pandac.PandaModules import WindowProperties

from PyQt5.QtCore import pyqtProperty, pyqtSignal, qFuzzyCompare, QObject, QPropertyAnimation # pylint: disable=no-name-in-module
from PyQt5.QtGui import QMatrix4x4, QQuaternion, QVector3D # pylint: disable=no-name-in-module
from PyQt5 import QtWidgets,QtCore,QtGui,Qt , Qt3DAnimation,Qt3DCore,Qt3DExtras,Qt3DInput,Qt3DLogic,Qt3DRender , QtQml
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView,QWebEngineSettings # pylint: disable=no-name-in-module
except:
    from PyQtWebEngine.QtWebEngineWidgets import QWebEngineView,QWebEngineSettings

import sys

import AstusPandaEngine as ape
from AstusPandaEngine import base, window, engine

SupportsRenderPipeline = False

class scene(ape.APEScene):
    def start(self):
        #self.loader
        #self.camera.setPos(0, -28, 6)
        #self.win.setClearColorActive(True)
        #self.win.setClearColor(p3dc.VBase4(0, 0.5, 0, 1))        
        self.testModel = self.addModel(base().loader.loadModel('panda'),'panda')
        self.testModel.reparentTo(base().render)
        # This rotates the actor 180 degrees on heading and 90 degrees on pitch.
        myInterval4 = self.testModel.hprInterval(1.0, p3dc.Vec3(360, 0, 0))
        myInterval4.loop()

class EngineClass(ape.APE):
    def start(self):
        self.scene = scene()
        self.scene.start()

class AppClass(ape.APEApp):
    pass

class MainWindowClass(ape.APEWindow):
    pass

class PandaWidget(ape.PandaWidget):
    pass

class BaseClass(ape.APEPandaBase):
    pass
        
    
if __name__ == '__main__':
    ape.start(WindowTitle,EngineClass,BaseClass,AppClass,MainWindowClass,PandaWidget,True,SupportsRenderPipeline)