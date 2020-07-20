#!/usr/bin/env python

# Original Author: Josh Yelon
# Modified to work with APE: Robin Albers
# Date: 2020-07-20
#
# See the associated manual page for an explanation.
#
import datetime
import platform
WindowTitle = "APE-Fireflies-Example"
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
#from pandac.PandaModules import p3dc.WindowProperties

from PyQt5.QtCore import pyqtProperty, pyqtSignal, qFuzzyCompare, QObject, QPropertyAnimation # pylint: disable=no-name-in-module
from PyQt5.QtGui import QMatrix4x4, QQuaternion, QVector3D # pylint: disable=no-name-in-module
from PyQt5 import QtWidgets,QtCore,QtGui,Qt , Qt3DAnimation,Qt3DCore,Qt3DExtras,Qt3DInput,Qt3DLogic,Qt3DRender , QtQml
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView,QWebEngineSettings # pylint: disable=no-name-in-module
except:
    from PyQtWebEngine.QtWebEngineWidgets import QWebEngineView,QWebEngineSettings

import sys
sys.path.append('..')
import os
import random

import AstusPandaEngine as ape
from AstusPandaEngine import window, engine

#
from direct.gui.OnscreenText import OnscreenText
from direct.showbase.DirectObject import DirectObject
from direct.interval.MetaInterval import Sequence
from direct.task.Task import Task
from direct.actor.Actor import Actor

#region Helper functions
# Function to put instructions on the screen.
def addInstructions(pos, msg):
    return OnscreenText(text=msg, style=1, fg=(1, 1, 1, 1), shadow=(0, 0, 0, 1),
                        parent=ape.base().a2dTopLeft, align=p3dc.TextNode.ALeft,
                        pos=(0.08, -pos - 0.04), scale=.05)

# Function to put title on the screen.
def addTitle(text):
    return OnscreenText(text=text, style=1, pos=(-0.1, 0.09), scale=.08,
                        parent=ape.base().a2dBottomRight, align=p3dc.TextNode.ARight,
                        fg=(1, 1, 1, 1), shadow=(0, 0, 0, 1))
#endregion helper functions


##

class scene(ape.APEScene):
    def start(self):
        ape.base().start()

class EngineClass(ape.APE):
    def start(self):
        self.scene = scene()
        self.scene.start()

class AppClass(ape.APEApp):
    pass

class MainWindowClass(ape.APEWindow):
    def setupUI(self):
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setContentsMargins(0,0,0,0)
        self.main_layout.addWidget(self.pandaContainer)
        self.dialLayout = QtWidgets.QHBoxLayout()
        self.dialLayout.setContentsMargins(0,0,0,0)
        self.dialLayoutWidget = QtWidgets.QWidget(self)
        self.dialLayoutWidget.setLayout(self.dialLayout)
        self.main_layout.addWidget(self.dialLayoutWidget)
        self.sizeDialLabel = QtWidgets.QLabel("Firefly Size",self)
        self.sizeDial = QtWidgets.QDoubleSpinBox(self)
        self.sizeDial.setMinimum(2)
        self.sizeDial.setMaximum(120)
        self.sizeDial.valueChanged.connect(self.setFireflySize)
        self.dialLayout.addWidget(self.sizeDialLabel)
        self.dialLayout.addWidget(self.sizeDial)

        #self.lineedit = QtWidgets.QLineEdit("Write something...does it work?")
        #layout.addWidget(self.lineedit)
        
        self.cw.setLayout(self.main_layout)

    def updateReadout(self):
        ape.base().inst2.destroy()
        ape.base().inst2 = addInstructions(0.12,
            "Up/Down: More / Fewer Fireflies (Currently: %d)" % len(ape.base().fireflies))
        ape.base().inst3.destroy()
        ape.base().inst3 = addInstructions(0.18,
            "Right/Left: Bigger / Smaller Fireflies (Radius: %d ft)" % ape.base().fireflysize)

    def toggleCards(self):
        ape.base().bufferViewer.toggleEnable()
        # When the cards are not visible, I also disable the color clear.
        # This color-clear is actually not necessary, the depth-clear is
        # sufficient for the purposes of the algorithm.
        if (ape.base().bufferViewer.isEnabled()):
            ape.base().modelbuffer.setClearColorActive(True)
        else:
            ape.base().modelbuffer.setClearColorActive(False)

    def incFireflyCount(self, scale):
        n = int((len(ape.base().fireflies) * scale) + 1)
        while (n > len(ape.base().fireflies)):
            ape.base().addFirefly()
        ape.base().updateReadout()

    def decFireflyCount(self, scale):
        n = int(len(ape.base().fireflies) * scale)
        if (n < 1):
            n = 1
        while (len(ape.base().fireflies) > n):
            ape.base().glowspheres.pop()
            ape.base().sequences.pop().finish()
            ape.base().scaleseqs.pop().finish()
            ape.base().fireflies.pop().removeNode()
        ape.base().updateReadout()

    def setFireflySize(self, n):
        ape.base().fireflysize = n
        for x in ape.base().glowspheres:
            x.setScale(ape.base().fireflysize * 1.1)
        ape.base().updateReadout()

class PandaWidget(ape.PandaWidget):
    pass

class BaseClass(ape.APEPandaBase):
    def start(self):
        self.setBackgroundColor((0, 0, 0, 0))

        # Preliminary capabilities check.

        if not self.win.getGsg().getSupportsBasicShaders():
            self.t = addTitle("Firefly Demo: Video driver reports that Cg "
                              "shaders are not supported.")
            return
        if not self.win.getGsg().getSupportsDepthTexture():
            self.t = addTitle("Firefly Demo: Video driver reports that depth "
                              "textures are not supported.")
            return

        # This algorithm uses two offscreen buffers, one of which has
        # an auxiliary bitplane, and the offscreen buffers share a single
        # depth buffer.  This is a heck of a complicated buffer setup.

        self.modelbuffer = self.makeFBO("model buffer", 1)
        self.lightbuffer = self.makeFBO("light buffer", 0)

        # Creation of a high-powered buffer can fail, if the graphics card
        # doesn't support the necessary OpenGL extensions.

        if self.modelbuffer is None or self.lightbuffer is None:
            self.t = addTitle("Firefly Demo: Video driver does not support "
                              "multiple render targets")
            return

        # Create four render textures: depth, normal, albedo, and final.
        # attach them to the various bitplanes of the offscreen buffers.

        self.texDepth = p3dc.Texture()
        self.texDepth.setFormat(p3dc.Texture.FDepthStencil)
        self.texAlbedo = p3dc.Texture()
        self.texNormal = p3dc.Texture()
        self.texFinal = p3dc.Texture()

        self.modelbuffer.addRenderTexture(self.texDepth,
            p3dc.GraphicsOutput.RTMBindOrCopy, p3dc.GraphicsOutput.RTPDepthStencil)
        self.modelbuffer.addRenderTexture(self.texAlbedo,
            p3dc.GraphicsOutput.RTMBindOrCopy, p3dc.GraphicsOutput.RTPColor)
        self.modelbuffer.addRenderTexture(self.texNormal,
            p3dc.GraphicsOutput.RTMBindOrCopy, p3dc.GraphicsOutput.RTPAuxRgba0)

        self.lightbuffer.addRenderTexture(self.texFinal,
            p3dc.GraphicsOutput.RTMBindOrCopy, p3dc.GraphicsOutput.RTPColor)

        # Set the near and far clipping planes.

        self.cam.node().getLens().setNear(50.0)
        self.cam.node().getLens().setFar(500.0)
        lens = self.cam.node().getLens()

        # This algorithm uses three cameras: one to render the models into the
        # model buffer, one to render the lights into the light buffer, and
        # one to render "plain" stuff (non-deferred shaded) stuff into the
        # light buffer.  Each camera has a bitmask to identify it.

        self.modelMask = 1
        self.lightMask = 2
        self.plainMask = 4

        self.modelcam = self.makeCamera(self.modelbuffer,
            lens=lens, scene=render, mask=self.modelMask)
        self.lightcam = self.makeCamera(self.lightbuffer,
            lens=lens, scene=render, mask=self.lightMask)
        self.plaincam = self.makeCamera(self.lightbuffer,
            lens=lens, scene=render, mask=self.plainMask)

        # Panda's main camera is not used.

        self.cam.node().setActive(0)

        # Take explicit control over the order in which the three
        # buffers are rendered.

        self.modelbuffer.setSort(1)
        self.lightbuffer.setSort(2)
        self.win.setSort(3)

        # Within the light buffer, control the order of the two cams.

        self.lightcam.node().getDisplayRegion(0).setSort(1)
        self.plaincam.node().getDisplayRegion(0).setSort(2)

        # By default, panda usually clears the screen before every
        # camera and before every window.  Tell it not to do that.
        # Then, tell it specifically when to clear and what to clear.

        self.modelcam.node().getDisplayRegion(0).disableClears()
        self.lightcam.node().getDisplayRegion(0).disableClears()
        self.plaincam.node().getDisplayRegion(0).disableClears()
        self.cam.node().getDisplayRegion(0).disableClears()
        self.cam2d.node().getDisplayRegion(0).disableClears()
        self.modelbuffer.disableClears()
        self.win.disableClears()

        self.modelbuffer.setClearColorActive(1)
        self.modelbuffer.setClearDepthActive(1)
        self.lightbuffer.setClearColorActive(1)
        self.lightbuffer.setClearColor((0, 0, 0, 1))

        # Miscellaneous stuff.

        self.disableMouse()
        self.camera.setPos(-9.112, -211.077, 46.951)
        self.camera.setHpr(0, -7.5, 2.4)
        random.seed()

        # Calculate the projection parameters for the final shader.
        # The math here is too complex to explain in an inline comment,
        # I've put in a full explanation into the HTML intro.

        proj = self.cam.node().getLens().getProjectionMat()
        proj_x = 0.5 * proj.getCell(3, 2) / proj.getCell(0, 0)
        proj_y = 0.5 * proj.getCell(3, 2)
        proj_z = 0.5 * proj.getCell(3, 2) / proj.getCell(2, 1)
        proj_w = -0.5 - 0.5 * proj.getCell(1, 2)

        # Configure the render state of the model camera.

        tempnode = p3dc.NodePath(p3dc.PandaNode("temp node"))
        tempnode.setAttrib(
            p3dc.AlphaTestAttrib.make(p3dc.RenderAttrib.MGreaterEqual, 0.5))
        tempnode.setShader(loader.loadShader("fireflies_model.sha"))
        tempnode.setAttrib(p3dc.DepthTestAttrib.make(p3dc.RenderAttrib.MLessEqual))
        self.modelcam.node().setInitialState(tempnode.getState())

        # Configure the render state of the light camera.

        tempnode = p3dc.NodePath(p3dc.PandaNode("temp node"))
        tempnode.setShader(loader.loadShader("fireflies_light.sha"))
        tempnode.setShaderInput("texnormal", self.texNormal)
        tempnode.setShaderInput("texalbedo", self.texAlbedo)
        tempnode.setShaderInput("texdepth", self.texDepth)
        tempnode.setShaderInput("proj", (proj_x, proj_y, proj_z, proj_w))
        tempnode.setAttrib(p3dc.ColorBlendAttrib.make(p3dc.ColorBlendAttrib.MAdd,
            p3dc.ColorBlendAttrib.OOne, p3dc.ColorBlendAttrib.OOne))
        tempnode.setAttrib(
            p3dc.CullFaceAttrib.make(p3dc.CullFaceAttrib.MCullCounterClockwise))
        # The next line causes problems on Linux.
        # tempnode.setAttrib(p3dc.DepthTestAttrib.make(p3dc.RenderAttrib.MGreaterEqual))
        tempnode.setAttrib(p3dc.DepthWriteAttrib.make(p3dc.DepthWriteAttrib.MOff))
        self.lightcam.node().setInitialState(tempnode.getState())

        # Configure the render state of the plain camera.

        rs = p3dc.RenderState.makeEmpty()
        self.plaincam.node().setInitialState(rs)

        # Clear any render attribs on the root node. This is necessary
        # because by default, panda assigns some attribs to the root
        # node.  These default attribs will override the
        # carefully-configured render attribs that we just attached
        # to the cameras.  The simplest solution is to just clear
        # them all out.

        render.setState(p3dc.RenderState.makeEmpty())

        # My artist created a model in which some of the polygons
        # don't have textures.  This confuses the shader I wrote.
        # This little hack guarantees that everything has a texture.

        white = loader.loadTexture("fireflies_models/white.jpg")
        render.setTexture(white, 0)

        # Create two subroots, to help speed cull traversal.

        self.lightroot = p3dc.NodePath(p3dc.PandaNode("lightroot"))
        self.lightroot.reparentTo(render)
        self.modelroot = p3dc.NodePath(p3dc.PandaNode("modelroot"))
        self.modelroot.reparentTo(render)
        self.lightroot.hide(p3dc.BitMask32(self.modelMask))
        self.modelroot.hide(p3dc.BitMask32(self.lightMask))
        self.modelroot.hide(p3dc.BitMask32(self.plainMask))

        # Load the model of a forest.  Make it visible to the model camera.
        # This is a big model, so we load it asynchronously while showing a
        # load text.  We do this by passing in a callback function.
        self.loading = addTitle("Loading models...")

        self.forest = p3dc.NodePath(p3dc.PandaNode("Forest Root"))
        self.forest.reparentTo(render)
        self.forest.hide(p3dc.BitMask32(self.lightMask | self.plainMask))
        loader.loadModel([
            "fireflies_models/background",
            "fireflies_models/foliage01",
            "fireflies_models/foliage02",
            "fireflies_models/foliage03",
            "fireflies_models/foliage04",
            "fireflies_models/foliage05",
            "fireflies_models/foliage06",
            "fireflies_models/foliage07",
            "fireflies_models/foliage08",
            "fireflies_models/foliage09"],
            callback=self.finishLoading)

        # Cause the final results to be rendered into the main window on a
        # card.

        self.card = self.lightbuffer.getTextureCard()
        self.card.setTexture(self.texFinal)
        self.card.reparentTo(render2d)

        # Panda contains a built-in viewer that lets you view the results of
        # your render-to-texture operations.  This code configures the viewer.

        self.bufferViewer.setPosition("llcorner")
        self.bufferViewer.setCardSize(0, 0.40)
        self.bufferViewer.setLayout("vline")
        self.toggleCards()
        self.toggleCards()

        # Firefly parameters

        self.fireflies = []
        self.sequences = []
        self.scaleseqs = []
        self.glowspheres = []
        self.fireflysize = 1.0
        self.spheremodel = loader.loadModel("misc/sphere")

        # Create the firefly model, a fuzzy dot
        dotSize = 1.0
        cm = p3dc.CardMaker("firefly")
        cm.setFrame(-dotSize, dotSize, -dotSize, dotSize)
        self.firefly = p3dc.NodePath(cm.generate())
        self.firefly.setTexture(loader.loadTexture("fireflies_models/firefly.png"))
        self.firefly.setAttrib(p3dc.ColorBlendAttrib.make(p3dc.ColorBlendAttrib.M_add,
            p3dc.ColorBlendAttrib.O_incoming_alpha, p3dc.ColorBlendAttrib.O_one))

        # these allow you to change parameters in realtime

        self.accept("arrow_up",   self.incFireflyCount, [1.1111111])
        self.accept("arrow_down", self.decFireflyCount, [0.9000000])
        self.accept("arrow_right", self.setFireflySize, [1.1111111])
        self.accept("arrow_left",  self.setFireflySize, [0.9000000])
        self.accept("v", self.toggleCards)
        self.accept("V", self.toggleCards)

    def finishLoading(self, models):
        # This function is used as callback to loader.loadModel, and called
        # when all of the models have finished loading.

        # Attach the models to the scene graph.
        for model in models:
            model.reparentTo(self.forest)

        # Show the instructions.
        self.loading.destroy()
        self.inst2 = addInstructions(0.12, "Up/Down: More / Fewer Fireflies (Count: unknown)")
        self.inst3 = addInstructions(0.18, "Right/Left: Bigger / Smaller Fireflies (Radius: unknown)")
        self.inst4 = addInstructions(0.24, "V: View the render-to-texture results")

        self.setFireflySize(25.0)
        while len(self.fireflies) < 5:
            self.addFirefly()
        self.updateReadout()

        self.nextadd = 0
        taskMgr.add(self.spawnTask, "spawner")

    def makeFBO(self, name, auxrgba):
        # This routine creates an offscreen buffer.  All the complicated
        # parameters are basically demanding capabilities from the offscreen
        # buffer - we demand that it be able to render to texture on every
        # bitplane, that it can support aux bitplanes, that it track
        # the size of the host window, that it can render to texture
        # cumulatively, and so forth.
        winprops = p3dc.WindowProperties()
        props = p3dc.FrameBufferProperties()
        props.setRgbColor(True)
        props.setRgbaBits(8, 8, 8, 8)
        props.setDepthBits(1)
        props.setAuxRgba(auxrgba)
        return self.graphicsEngine.makeOutput(
            self.pipe, "model buffer", -2,
            props, winprops,
            p3dc.GraphicsPipe.BFSizeTrackHost | p3dc.GraphicsPipe.BFCanBindEvery |
            p3dc.GraphicsPipe.BFRttCumulative | p3dc.GraphicsPipe.BFRefuseWindow,
            self.win.getGsg(), self.win)

    def addFirefly(self):
        pos1 = p3dc.LPoint3(random.uniform(-50, 50), random.uniform(-100, 150), random.uniform(-10, 80))
        dir = p3dc.LVector3(random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))
        dir.normalize()
        pos2 = pos1 + (dir * 20)
        fly = self.lightroot.attachNewNode(p3dc.PandaNode("fly"))
        glow = fly.attachNewNode(p3dc.PandaNode("glow"))
        dot = fly.attachNewNode(p3dc.PandaNode("dot"))
        color_r = 1.0
        color_g = random.uniform(0.8, 1.0)
        color_b = min(color_g, random.uniform(0.5, 1.0))
        fly.setColor(color_r, color_g, color_b, 1.0)
        fly.setShaderInput("lightcolor", (color_r, color_g, color_b, 1.0))
        int1 = fly.posInterval(random.uniform(7, 12), pos1, pos2)
        int2 = fly.posInterval(random.uniform(7, 12), pos2, pos1)
        si1 = fly.scaleInterval(random.uniform(0.8, 1.5),
            p3dc.LPoint3(0.2, 0.2, 0.2), p3dc.LPoint3(0.2, 0.2, 0.2))
        si2 = fly.scaleInterval(random.uniform(1.5, 0.8),
            p3dc.LPoint3(1.0, 1.0, 1.0), p3dc.LPoint3(0.2, 0.2, 0.2))
        si3 = fly.scaleInterval(random.uniform(1.0, 2.0),
            p3dc.LPoint3(0.2, 0.2, 0.2), p3dc.LPoint3(1.0, 1.0, 1.0))
        siseq = Sequence(si1, si2, si3)
        siseq.loop()
        siseq.setT(random.uniform(0, 1000))
        seq = Sequence(int1, int2)
        seq.loop()
        self.spheremodel.instanceTo(glow)
        self.firefly.instanceTo(dot)
        glow.setScale(self.fireflysize * 1.1)
        glow.hide(p3dc.BitMask32(self.modelMask | self.plainMask))
        dot.hide(p3dc.BitMask32(self.modelMask | self.lightMask))
        dot.setColor(color_r, color_g, color_b, 1.0)
        self.fireflies.append(fly)
        self.sequences.append(seq)
        self.glowspheres.append(glow)
        self.scaleseqs.append(siseq)

    def updateReadout(self):
        self.inst2.destroy()
        self.inst2 = addInstructions(0.12,
            "Up/Down: More / Fewer Fireflies (Currently: %d)" % len(self.fireflies))
        self.inst3.destroy()
        self.inst3 = addInstructions(0.18,
            "Right/Left: Bigger / Smaller Fireflies (Radius: %d ft)" % self.fireflysize)

    def toggleCards(self):
        self.bufferViewer.toggleEnable()
        # When the cards are not visible, I also disable the color clear.
        # This color-clear is actually not necessary, the depth-clear is
        # sufficient for the purposes of the algorithm.
        if (self.bufferViewer.isEnabled()):
            self.modelbuffer.setClearColorActive(True)
        else:
            self.modelbuffer.setClearColorActive(False)

    def incFireflyCount(self, scale):
        n = int((len(self.fireflies) * scale) + 1)
        while (n > len(self.fireflies)):
            self.addFirefly()
        self.updateReadout()

    def decFireflyCount(self, scale):
        n = int(len(self.fireflies) * scale)
        if (n < 1):
            n = 1
        while (len(self.fireflies) > n):
            self.glowspheres.pop()
            self.sequences.pop().finish()
            self.scaleseqs.pop().finish()
            self.fireflies.pop().removeNode()
        self.updateReadout()

    def setFireflySize(self, n):
        n = n * self.fireflysize
        self.fireflysize = n
        for x in self.glowspheres:
            x.setScale(self.fireflysize * 1.1)
        self.updateReadout()
        window().sizeDial.blockSignals(True)
        window().sizeDial.setValue(self.fireflysize)
        window().sizeDial.blockSignals(False)

    def spawnTask(self, task):
        if task.time > self.nextadd:
            self.nextadd = task.time + 1.0
            if (len(self.fireflies) < 300):
                self.incFireflyCount(1.03)
        return Task.cont

if __name__ == '__main__':
    ape.start(WindowTitle,EngineClass,BaseClass,AppClass,MainWindowClass,PandaWidget,True)
