#!/usr/bin/env python
# Updated to APE by Robin Albers
#
# Last Updated: 2020-07-21

import datetime
import platform
WindowTitle = "APE-Shadows-Advanced-Example"
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

# Python imports
import os
import random
import sys
sys.path.append('..')

# Panda imports
import panda3d as p3d
import panda3d.core as p3dc
from direct.showbase.ShowBase import ShowBase
from direct.showbase.DirectObject import DirectObject
from direct.gui.OnscreenText import OnscreenText
from direct.actor.Actor import Actor
#from direct.interval.IntervalGlobal import

# AGE and APE imports
import AGeLib as age # pylint: disable=import-error
from AGeLib import NC # pylint: disable=import-error

import AstusPandaEngine as ape # pylint: disable=import-error
from AstusPandaEngine import window, engine # pylint: disable=import-error

# Qt imports
from PyQt5.QtCore import pyqtProperty, pyqtSignal, qFuzzyCompare, QObject, QPropertyAnimation # pylint: disable=no-name-in-module
from PyQt5.QtGui import QMatrix4x4, QQuaternion, QVector3D # pylint: disable=no-name-in-module
from PyQt5 import QtWidgets,QtCore,QtGui,Qt , Qt3DAnimation,Qt3DCore,Qt3DExtras,Qt3DInput,Qt3DLogic,Qt3DRender , QtQml
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView,QWebEngineSettings # pylint: disable=no-name-in-module
except:
    from PyQtWebEngine.QtWebEngineWidgets import QWebEngineView,QWebEngineSettings

#

#region Helper functions
# Function to put instructions on the screen.
def addInstructions(pos, msg):
    return OnscreenText(text=msg, style=1, fg=(1, 1, 1, 1), scale=.05,
                        shadow=(0, 0, 0, 1), parent=ape.base().a2dTopLeft,
                        pos=(0.08, -pos - 0.04), align=p3dc.TextNode.ALeft)

# Function to put title on the screen.
def addTitle(text):
    return OnscreenText(text=text, style=1, fg=(1, 1, 1, 1), scale=.07,
                        parent=ape.base().a2dBottomRight, align=p3dc.TextNode.ARight,
                        pos=(-0.1, 0.09), shadow=(0, 0, 0, 1))
#endregion Helper functions


class scene(ape.APEScene):
    def start(self):
        World()

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

class World(DirectObject):

    def __init__(self):
        # Preliminary capabilities check.

        if not ape.base().win.getGsg().getSupportsBasicShaders():
            self.t = addTitle(
                "Shadow Demo: Video driver reports that shaders are not supported.")
            return
        if not ape.base().win.getGsg().getSupportsDepthTexture():
            self.t = addTitle(
                "Shadow Demo: Video driver reports that depth textures are not supported.")
            return

        # creating the offscreen buffer.

        winprops = p3dc.WindowProperties(size=(512, 512))
        props = p3dc.FrameBufferProperties()
        props.setRgbColor(1)
        props.setAlphaBits(1)
        props.setDepthBits(1)
        LBuffer = ape.base().graphicsEngine.makeOutput(
            ape.base().pipe, "offscreen buffer", -2,
            props, winprops,
            p3dc.GraphicsPipe.BFRefuseWindow,
            ape.base().win.getGsg(), ape.base().win)
        self.buffer = LBuffer

        if not LBuffer:
            self.t = addTitle(
                "Shadow Demo: Video driver cannot create an offscreen buffer.")
            return

        Ldepthmap = p3dc.Texture()
        LBuffer.addRenderTexture(Ldepthmap, p3dc.GraphicsOutput.RTMBindOrCopy,
                                 p3dc.GraphicsOutput.RTPDepthStencil)
        if ape.base().win.getGsg().getSupportsShadowFilter():
            Ldepthmap.setMinfilter(p3dc.Texture.FTShadow)
            Ldepthmap.setMagfilter(p3dc.Texture.FTShadow)

        # Adding a color texture is totally unnecessary, but it helps with
        # debugging.
        Lcolormap = p3dc.Texture()
        LBuffer.addRenderTexture(Lcolormap, p3dc.GraphicsOutput.RTMBindOrCopy,
                                 p3dc.GraphicsOutput.RTPColor)

        self.inst_p = addInstructions(0.06, 'P : stop/start the Panda Rotation')
        self.inst_w = addInstructions(0.12, 'W : stop/start the Walk Cycle')
        self.inst_t = addInstructions(0.18, 'T : stop/start the Teapot')
        self.inst_l = addInstructions(0.24, 'L : move light source far or close')
        self.inst_v = addInstructions(0.30, 'V : View the Depth-Texture results')
        self.inst_u = addInstructions(0.36, 'U : toggle updating the shadow map')
        self.inst_x = addInstructions(0.42, 'Left/Right Arrow : switch camera angles')
        self.inst_a = addInstructions(0.48, 'Something about A/Z and push bias')

        ape.base().setBackgroundColor(0, 0, 0.2, 1)

        ape.base().camLens.setNearFar(1.0, 10000)
        ape.base().camLens.setFov(75)
        ape.base().disableMouse()

        # Load the scene.

        floorTex = ape.loader().loadTexture('maps/envir-ground.jpg')
        cm = p3dc.CardMaker('')
        cm.setFrame(-2, 2, -2, 2)
        floor = ape.render().attachNewNode(p3dc.PandaNode("floor"))
        for y in range(12):
            for x in range(12):
                nn = floor.attachNewNode(cm.generate())
                nn.setP(-90)
                nn.setPos((x - 6) * 4, (y - 6) * 4, 0)
        floor.setTexture(floorTex)
        floor.flattenStrong()

        self.pandaAxis = ape.render().attachNewNode('panda axis')
        self.pandaModel = Actor('panda-model', {'walk': 'panda-walk4'})
        self.pandaModel.reparentTo(self.pandaAxis)
        self.pandaModel.setPos(9, 0, 0)
        self.pandaModel.setShaderInput("scale", (0.01, 0.01, 0.01, 1.0))
        self.pandaWalk = self.pandaModel.actorInterval('walk', playRate=1.8)
        self.pandaWalk.loop()
        self.pandaMovement = self.pandaAxis.hprInterval(
            20.0, p3dc.LPoint3(-360, 0, 0), startHpr=p3dc.LPoint3(0, 0, 0))
        self.pandaMovement.loop()

        self.teapot = ape.loader().loadModel('teapot')
        self.teapot.reparentTo(ape.render())
        self.teapot.setPos(0, -20, 10)
        self.teapot.setShaderInput("texDisable", (1, 1, 1, 1))
        self.teapotMovement = self.teapot.hprInterval(50, p3dc.LPoint3(0, 360, 360))
        self.teapotMovement.loop()

        self.accept('escape', sys.exit)

        self.accept("arrow_left", self.incrementCameraPosition, [-1])
        self.accept("arrow_right", self.incrementCameraPosition, [1])
        self.accept("p", self.toggleInterval, [self.pandaMovement])
        self.accept("t", self.toggleInterval, [self.teapotMovement])
        self.accept("w", self.toggleInterval, [self.pandaWalk])
        self.accept("v", ape.base().bufferViewer.toggleEnable)
        self.accept("u", self.toggleUpdateShadowMap)
        self.accept("l", self.incrementLightPosition, [1])
        self.accept("o", ape.base().oobe)
        self.accept('a', self.adjustPushBias, [1.1])
        self.accept('z', self.adjustPushBias, [0.9])

        self.LCam = ape.base().makeCamera(LBuffer)
        self.LCam.node().setScene(ape.render())
        self.LCam.node().getLens().setFov(40)
        self.LCam.node().getLens().setNearFar(10, 100)

        # default values
        self.pushBias = 0.04
        self.ambient = 0.2
        self.cameraSelection = 0
        self.lightSelection = 0

        # setting up shader
        ape.render().setShaderInput('light', self.LCam)
        ape.render().setShaderInput('Ldepthmap', Ldepthmap)
        ape.render().setShaderInput('ambient', (self.ambient, 0, 0, 1.0))
        ape.render().setShaderInput('texDisable', (0, 0, 0, 0))
        ape.render().setShaderInput('scale', (1, 1, 1, 1))

        # Put a shader on the Light camera.
        lci = p3dc.NodePath(p3dc.PandaNode("Light Camera Initializer"))
        lci.setShader(ape.loader().loadShader('shadows_caster.sha'))
        self.LCam.node().setInitialState(lci.getState())

        # Put a shader on the Main camera.
        # Some video cards have special hardware for shadow maps.
        # If the card has that, use it.  If not, use a different
        # shader that does not require hardware support.

        mci = p3dc.NodePath(p3dc.PandaNode("Main Camera Initializer"))
        if ape.base().win.getGsg().getSupportsShadowFilter():
            mci.setShader(ape.loader().loadShader('shadows_shadow.sha'))
        else:
            mci.setShader(ape.loader().loadShader('shadows_shadow-nosupport.sha'))
        ape.base().cam.node().setInitialState(mci.getState())

        self.incrementCameraPosition(0)
        self.incrementLightPosition(0)
        self.adjustPushBias(1.0)

    def toggleInterval(self, ival):
        if ival.isPlaying():
            ival.pause()
        else:
            ival.resume()

    def toggleUpdateShadowMap(self):
        self.buffer.active = not self.buffer.active

    def incrementCameraPosition(self, n):
        self.cameraSelection = (self.cameraSelection + n) % 6
        if (self.cameraSelection == 0):
            ape.base().cam.reparentTo(ape.render())
            ape.base().cam.setPos(30, -45, 26)
            ape.base().cam.lookAt(0, 0, 0)
            self.LCam.node().hideFrustum()
        if (self.cameraSelection == 1):
            ape.base().cam.reparentTo(self.pandaModel)
            ape.base().cam.setPos(7, -3, 9)
            ape.base().cam.lookAt(0, 0, 0)
            self.LCam.node().hideFrustum()
        if (self.cameraSelection == 2):
            ape.base().cam.reparentTo(self.pandaModel)
            ape.base().cam.setPos(-7, -3, 9)
            ape.base().cam.lookAt(0, 0, 0)
            self.LCam.node().hideFrustum()
        if (self.cameraSelection == 3):
            ape.base().cam.reparentTo(ape.render())
            ape.base().cam.setPos(7, -23, 12)
            ape.base().cam.lookAt(self.teapot)
            self.LCam.node().hideFrustum()
        if (self.cameraSelection == 4):
            ape.base().cam.reparentTo(ape.render())
            ape.base().cam.setPos(-7, -23, 12)
            ape.base().cam.lookAt(self.teapot)
            self.LCam.node().hideFrustum()
        if (self.cameraSelection == 5):
            ape.base().cam.reparentTo(ape.render())
            ape.base().cam.setPos(1000, 0, 195)
            ape.base().cam.lookAt(0, 0, 0)
            self.LCam.node().showFrustum()

    def incrementLightPosition(self, n):
        self.lightSelection = (self.lightSelection + n) % 2
        if (self.lightSelection == 0):
            self.LCam.setPos(0, -40, 25)
            self.LCam.lookAt(0, -10, 0)
            self.LCam.node().getLens().setNearFar(10, 100)
        if (self.lightSelection == 1):
            self.LCam.setPos(0, -600, 200)
            self.LCam.lookAt(0, -10, 0)
            self.LCam.node().getLens().setNearFar(10, 1000)

    def shaderSupported(self):
        return ape.base().win.getGsg().getSupportsBasicShaders() and \
               ape.base().win.getGsg().getSupportsDepthTexture() and \
               ape.base().win.getGsg().getSupportsShadowFilter()

    def adjustPushBias(self, inc):
        self.pushBias *= inc
        self.inst_a.setText(
            'A/Z: Increase/Decrease the Push-Bias [%F]' % self.pushBias)
        ape.render().setShaderInput('push', self.pushBias)

if __name__ == '__main__':
    ape.start(WindowTitle,EngineClass,BaseClass,AppClass,MainWindowClass,PandaWidget,True)
