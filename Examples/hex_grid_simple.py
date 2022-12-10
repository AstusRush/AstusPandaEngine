# This example shows how to generate a simple hex grid with click detection
# Author: Robin "Astus" Albers
# Models: Robin "Astus" Albers

SupportsRenderPipeline = False

import datetime
import platform
WindowTitle = "APE-Simple-Hex-Grid-Example"
if __name__ == "__main__":
    print()
    print(datetime.datetime.now().strftime('%H:%M:%S'))
    print(WindowTitle)
    print("Loading Modules")#, end = "")
    if platform.system() == 'Windows':
        try:
            import ctypes
            myAppId = u'{}{}'.format(WindowTitle , datetime.datetime.now().strftime('%H:%M:%S')) # arbitrary string
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myAppId)
        except:
            pass

# Python imports
import sys
sys.path.append('..')
import os
import random
import typing
import importlib
import inspect

import numpy as np

# Panda imports
import panda3d as p3d
import panda3d.core as p3dc
from direct.gui.OnscreenText import OnscreenText
from direct.task.Task import Task

# AGE and APE imports
from AGeLib import *

import AstusPandaEngine as ape # pylint: disable = import-error
from AstusPandaEngine import window, engine, base, render, loader # pylint: disable = import-error


HIGHLIGHT = (0, 1, 1, 1)

class HexScene(ape.APEScene):
    # Macro-like function to reduce the amount of code needed to create the
    # onscreen instructions
    def makeStatusLabel(self, i):
        return OnscreenText(
            parent=base().a2dTopLeft, align=p3dc.TextNode.ALeft,
            style=1, fg=(1, 1, 0, 1), shadow=(0, 0, 0, .4),
            pos=(0.06, -0.1 -(.06 * i)), scale=.05, mayChange=True)
    
    def start(self):
        
        ape.base().win.setClearColor(p3dc.Vec4(0,0,0,1))
        
        # This code puts the standard title and instruction text on screen
        self.mouseText = self.makeStatusLabel(0)
        self.mouseText.setText("Left-click: Send notification with the hex name")
        self.spaceText = self.makeStatusLabel(1)
        self.spaceText.setText("SPACE: Cycle camera positions")
        ## 
        # Finally call the function that builds the instruction texts
        self.nextCamPos = 1
        base().accept("space", self.toggleCam)  # releasing places it

    def toggleCam(self):
        if self.nextCamPos == 0:
            base().camera.setPosHpr(0, -12, 8, 0, -35, 0)  # Set the camera
            self.nextCamPos = 1
        elif self.nextCamPos == 1:
            base().camera.setPosHpr(0, 12, 8, 180, -35, 0)  # Set the camera
            self.nextCamPos = 2
        elif self.nextCamPos == 2:
            base().camera.setPosHpr(-12, 0, 8, -90, -35, 0)  # Set the camera
            self.nextCamPos = 3
        elif self.nextCamPos == 3:
            base().camera.setPosHpr(4, -12, 4, 18, -15, 0)  # Set the camera
            self.nextCamPos = 4
        elif self.nextCamPos == 4:
            base().camera.setPosHpr(0, 0, 18, 0, -90, 0)  # Set the camera
            self.nextCamPos = 5
        elif self.nextCamPos == 5:
            base().camera.setPosHpr(30, -30, 45, 45, -45, 0)  # Set the camera
            self.nextCamPos = 6
        elif self.nextCamPos == 6:
            base().camera.setPosHpr(0, 0, -18, 0, 90, 0)  # Set the camera
            self.nextCamPos = 0

#region Hex Map
class HexGrid():
    def __init__(self, scene:ape.APEScene=None, root:p3dc.NodePath = None, size: typing.Tuple[int,int] = (10,10)) -> None:
        self.Scene = scene if scene else engine().Scene
        if root:
            self.Root = root
        else:
            self.Root = render().attachNewNode("hexRoot")
            self.Root.setPos((0,0,0))
        self.Hexes = []
        self.Size = size
        self.m_material = None
        self.m_colour = None
        self.generateHex()
        
        # This will represent the index of the currently highlighted hex
        self.hiSq = False
        
        # Start the task that handles the picking
        self.mouseTask = base().taskMgr.add(self._mouseTask, 'mouseTask')
        base().accept("mouse1", self.hexClicked)
        
    def clearHexes(self):
        for i in self.Hexes:
            for j in i:
                #self.Root.removeNode(j.model)
                del j
            del i
        del self.Hexes
        #self._Hexes = self.Hexes
        self.Hexes = []
        
    def generateHex(self):
        self.clearHexes()
        #TODO: When the number oh Hexes is even the offset must be subtracted from the first limit but if it is odd half the offset bust be +/- to both!
        limx1 = -self.Size[0]/2*3/2
        limx2 = self.Size[0]/2*3/2 - 3/2
        limy1 = -self.Size[1]/2*np.sqrt(3)
        limy2 = self.Size[1]/2*np.sqrt(3)-np.sqrt(3)
        
        for i,x in enumerate(np.linspace(limx1, limx2, self.Size[0])):
            l = []
            for j,y in enumerate(np.linspace(limy1, limy2, self.Size[1])):
                if i%2:
                    y += np.sqrt(3)/2
                l.append(_Hex(self.Scene, self.Root, f"Hex ({i},{j})", (i,j), (y,x,0), random.choice(list(App().PenColours.values())).color()))
            self.Hexes.append(l)
            
    def getHex(self, i:typing.Tuple[int,int]):
        r:_Hex = self.Hexes[i[0]][i[1]]
        return r

    def _mouseTask(self, task):
        # This task deals with the highlighting and dragging based on the mouse
        
        # First, clear the current highlight
        if self.hiSq is not False:
            self.getHex(self.hiSq).setColor(random.choice(list(App().PenColours.values())).color())
            self.hiSq = False
        
        # Check to see if we can access the mouse. We need it to do anything else
        if base().mouseWatcherNode.hasMouse():
            # get the mouse position
            mpos = base().mouseWatcherNode.getMouse()
            
            # Set the position of the ray based on the mouse position
            base().pickerRay.setFromLens(base().camNode, mpos.getX(), mpos.getY())
            
            # Do the actual collision pass (Do it only on the squares for efficiency purposes)
            base().picker.traverse(self.Root)
            if base().pq.getNumEntries() > 0:
                # if we have hit something, sort the hits so that the closest is first, and highlight that node
                base().pq.sortEntries()
                i:str = base().pq.getEntry(0).getIntoNode().getTag('hex')
                i = (int(i.split(" ")[0]), int(i.split(" ")[1]))
                # Set the highlight on the picked square
                self.getHex(i).setColor(HIGHLIGHT)
                self.hiSq = i
        
        return Task.cont

    def hexClicked(self):
        NC(10,self.getHex(self.hiSq).Name,input=self.getHex(self.hiSq).pos)

class _Hex():
    def __init__(self, scene:ape.APEScene, root, name:str, coord, pos:typing.Tuple[int,int,int], mat: QtGui.QColor):
        try:
            self.Name = name
            self.m_mesh = None
            self.m_material = None
            self.m_colour = mat
            self.Coord = coord
            self.pos = p3dc.LPoint3(pos)
            mesh = "simple_models/hexagon.ply"
            # Load, parent, colour and position the model (a single square polygon)
            self.model = loader().loadModel(mesh)
            self.model.reparentTo(root)
            self.model.setPos(self.pos)
            self.model.setColor(ape.colour(self.m_colour))
            # Set the model itself to be collideable with the ray. If this model was
            # any more complex than a single polygon, you should set up a collision
            # sphere around it instead. But for single polygons this works fine.
            #self.model.find("**/polygon").node().setIntoCollideMask(p3dc.BitMask32.bit(1)) # Seems to only work with .egg but not with .ply
            self.model.find("").node().setIntoCollideMask(p3dc.BitMask32.bit(1)) # the model only has a single nodePath and that one has no name. Therefore we call .find("")
            # Set a tag on the square's node so we can look up what square this is later during the collision pass
            # We will use this variable as a pointer to whatever piece is currently in this square
            #self.model.find("**/polygon").node().setTag('hex', str(coord[0])+" "+str(coord[1])) # Seems to only work with .egg but not with .ply
            self.model.find("").node().setTag('hex', str(coord[0])+" "+str(coord[1])) # the model only has a single nodePath and that one has no name. Therefore we call .find("")
        except:
            NC(1,f"Error while creating {name}",exc=True)
        
    def __del__(self):
        self.model.removeNode()
        print(self.Name,"has been deleted")
    
    def setColor(self,color):
        self.model.setColor(ape.colour(color))
    
#endregion Hex Map

#region  main


# Function to put instructions on the screen.

class BaseClass(ape.APEPandaBase):
    def start(self):
        if self.render_pipeline:
            # Set time of day
            self.render_pipeline.daytime_mgr.time = "5:20"
            
            # Use a special effect for rendering the scene, this is because the
            # roaming ralph model has no normals or valid materials
            self.render_pipeline.set_effect(ape.render(), "_pipeline_effect-texture.yaml", {}, sort=250)
        
        self.disableMouse()  # Disable mouse camera control
        self.camera.setPosHpr(0, -12, 8, 0, -35, 0)  # Set the camera
        
        # Since we are using collision detection to do picking, we set it up like
        # any other collision detection system with a traverser and a handler
        self.picker = p3dc.CollisionTraverser()  # Make a traverser
        self.pq = p3dc.CollisionHandlerQueue()  # Make a handler
        # Make a collision node for our picker ray
        self.pickerNode = p3dc.CollisionNode('mouseRay')
        # Attach that node to the camera since the ray will need to be positioned relative to it
        self.pickerNP = self.camera.attachNewNode(self.pickerNode)
        # Everything to be picked will use bit 1. This way if we were doing other collision we could separate it
        self.pickerNode.setFromCollideMask(p3dc.BitMask32.bit(1))
        self.pickerRay = p3dc.CollisionRay()  # Make our ray
        # Add it to the collision node
        self.pickerNode.addSolid(self.pickerRay)
        # Register the ray as something that can cause collisions
        self.picker.addCollider(self.pickerNP, self.pq)
        #self.picker.showCollisions(render) # uncomment this to show the collisions
        
class EngineClass(ape.APE):
    def start(self):
        self.base.start()
        self.Scene = HexScene()
        self.Scene.start()
        window().start()

class AppClass(ape.APEApp):
    pass

class MainWindowClass(ape.APELabWindow):
    def setupUI(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.PandaContainer)
        
        self.genWidget = QtWidgets.QWidget(self)
        genLayout = QtWidgets.QHBoxLayout()
        genLayout.setContentsMargins(0,0,0,0)
        
        self.genButton = AGeWidgets.Button(self,"Regenerate the hex grid",lambda: self.gen())
        genLayout.addWidget(self.genButton)
        
        self.genWidget.setLayout(genLayout)
        layout.addWidget(self.genWidget)
        
        self.cw.setLayout(layout)
        
        self.Console1.setText("self.HexGrid = HexGrid()\n")
    
    def gen(self):
        self.HexGrid.generateHex()
            
    def start(self):
        self.HexGrid = HexGrid()

class PandaWidget(ape.PandaWidget):
    pass


#endregion real main
if __name__ == '__main__':
    ape.start(WindowTitle, EngineClass, BaseClass, AppClass, MainWindowClass, PandaWidget, True, SupportsRenderPipeline)
