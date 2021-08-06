# This example explores a more advanced hexagonal grid which supports objects that can be moved from hex to hex per drag'n'drop
# TODO: add some chess pieces from the start
# Author: Robin "Astus" Albers
# Models: Robin "Astus" Albers (hexagon and ring) and Eddie Canaan (cool chess pieces)

SupportsRenderPipeline = False

import datetime
import platform
WindowTitle = "APE-Hex-Grid-drag-and-drop-Example"
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
from direct.showbase.ShowBase import ShowBase
from direct.showbase.DirectObject import DirectObject
from direct.gui.OnscreenText import OnscreenText
from direct.task.Task import Task
from direct.actor.Actor import Actor

# AGE and APE imports
from AGeLib import *

import AstusPandaEngine as ape
from AstusPandaEngine import engine, base, render, loader
from AstusPandaEngine import window as _window

def window():
    # type: () -> MainWindowClass
    #w:MainWindowClass = _window()
    return _window()#w

sys.path.append('..')

# This function, given a line (vector plus origin point) and a desired z value,
# will give us the point on the line where the desired z value is what we want.
# This is how we know where to position an object in 3D space based on a 2D mouse
# position. It also assumes that we are dragging in the XY plane.
#
# This is derived from the mathematical of a plane, solved for a given point
def PointAtZ(z, point, vec):
    return point + vec * ((z - point.getZ()) / vec.getZ())

# A handy little function for getting the proper position for a given square1
def getHexPos(i:typing.Tuple[int,int]):
    return window().getHex(i).Pos

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
        self.Hexes = [] # type: typing.List[_Hex]
        self.Size = size
        self.m_material = None
        self.m_colour = None
        self.generateHex()
        
        # This will represent the index of the currently highlighted hex
        self.hiSq = False # type: _Hex
        # This wil represent the index of the hex where currently dragged piece was grabbed from
        self.dragging = False # type: _Hex
        
        # Start the task that handles the picking
        self.mouseTask = base().taskMgr.add(self._mouseTask, 'mouseTask')
        base().accept("mouse1", self.grabPiece)
        base().accept("mouse1-up", self.releasePiece)
        base().accept("mouse2", self.sendHexNotification) # middle mouse button
        
    def clearHexes(self):
        for i in self.Hexes:
            for j in i:
                del j
            del i
        del self.Hexes
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
                l.append(_Hex(self.Scene, self.Root, f"Hex ({i},{j})", (i,j), (y,x,0), "Blue"))
            self.Hexes.append(l)
            
    def getHex(self, i:typing.Tuple[int,int]):
        r:_Hex = self.Hexes[i[0]][i[1]]
        return r
    
  #region Interaction
    def _mouseTask(self, task):
        # This task deals with the highlighting and dragging based on the mouse
        
        # First, clear the current highlight
        if self.hiSq is not False:
            self.hiSq.highlight(False)
            self.hiSq = False
        
        # Check to see if we can access the mouse. We need it to do anything else
        if base().mouseWatcherNode.hasMouse():
            # get the mouse position
            mpos = base().mouseWatcherNode.getMouse()
            
            # Set the position of the ray based on the mouse position
            base().pickerRay.setFromLens(base().camNode, mpos.getX(), mpos.getY())
            
            # If we are dragging something, set the position of the object
            # to be at the appropriate point over the plane of the board
            if self.dragging is not False:
                # Gets the point described by pickerRay.getOrigin(), which is relative to
                # camera, relative instead to render
                nearPoint = render().getRelativePoint( base().camera, base().pickerRay.getOrigin() )
                # Same thing with the direction of the ray
                nearVec  = render().getRelativeVector( base().camera, base().pickerRay.getDirection() )
                for i in self.dragging.content:
                    i.Node.setPos( PointAtZ(.5, nearPoint, nearVec) )
            
            # Do the actual collision pass (Do it only on the squares for efficiency purposes)
            base().picker.traverse(self.Root)
            if base().pq.getNumEntries() > 0:
                # if we have hit something, sort the hits so that the closest is first, and highlight that node
                base().pq.sortEntries()
                i:str = base().pq.getEntry(0).getIntoNode().getTag('hex')
                i = self.getHex((int(i.split(" ")[0]), int(i.split(" ")[1]))) # type: _Hex
                # Set the highlight on the picked square
                i.highlight()
                self.hiSq = i
        
        return Task.cont
    
    def sendHexNotification(self):
        if self.hiSq is not False:
            NC(10,self.hiSq.Name,input=self.hiSq.Pos)
    
    def grabPiece(self):
        # If a square is highlighted and it has a piece, set it to dragging mode
        if self.hiSq is not False and self.hiSq.content:
            self.dragging = self.hiSq
            self.hiSq = False
    
    def releasePiece(self):
        # Letting go of a piece. If we are not on a square, return it to its original
        # position. Otherwise, swap it with the piece in the new square
        # Make sure we really are dragging something
        if self.dragging is not False:
            # We have let go of the piece, but we are not on a square
            if self.hiSq is False:
                for i in self.dragging.content:
                    i.Node.setPos(self.dragging)
            else:
                # Otherwise, swap the pieces
                self.dragging.swapContentsWith(self.hiSq)
        
        # We are no longer dragging anything
        self.dragging = False
  #endregion Interaction

class _Hex():
    def __init__(self, scene:ape.APEScene, root, name:str, coordinates, pos:typing.Tuple[int,int,int], colour: str):
        try:
            # What we need:
            # - A hexagonal mesh for the click-detection and to highlight the hex
            # - A Hexagonal ring to highlight the edges of all hexes
            # - These two meshes must be as simple as possible but must be able to be visible, blink, and be hidden independently of one another
            #
            self.Name = name
            self.Colour = colour
            self.Coordinates = coordinates
            self.Pos = p3dc.LPoint3(pos)
            mesh = "simple_models/hexagon.ply"
            meshRing = "simple_models/hexagonRing.ply"
            # Load, parent, colour, and position the model (a hexagon-shaped ring consisting of 6 polygons)
            self.Model = loader().loadModel(meshRing)
            self.Model.reparentTo(root)
            self.Model.setPos(self.Pos)
            self.setColor(self.Colour)
            # Load, parent, hide, and position the face (a single hexagon polygon)
            self.Face = loader().loadModel(mesh)
            self.Face.reparentTo(self.Model)
            #self.Model.setPos(self.Pos)
            self.Face.setColor((0,0,0,0))
            self.Face.hide()
            # Set the Model itself to be collideable with the ray. If this Model was
            # any more complex than a single polygon, you should set up a collision
            # sphere around it instead. But for single polygons this works fine.
            self.Face.find("").node().setIntoCollideMask(p3dc.BitMask32.bit(1))
            # Set a tag on the square's node so we can look up what square this is later during the collision pass
            # We will use this variable as a pointer to whatever piece is currently in this square
            self.Face.find("").node().setTag('hex', str(coordinates[0])+" "+str(coordinates[1]))
            
            # We will use this list to store all objects that occupy this hexagon
            self.content = [] # type: typing.List[Object]
        except:
            NC(1,f"Error while creating {name}",exc=True)
    
    def __del__(self):
        del self.content
        self.Face.removeNode()
        self.Model.removeNode()
    
    def swapContentsWith(self,other):
        # type: (_Hex) -> None
        oContent = other.content
        other.content = self.content
        self.content = oContent
        for i in self.content:
            i.moveToHex(self)
        for i in other.content:
            i.moveToHex(other)
    
    def setColor(self,colour):
        if isinstance(colour,str):
            colour = App().PenColours[colour].color()
        self.Model.setColor(ape.colour(colour))
        
    def highlight(self, highlight:bool = True):
        if highlight:
            self.setColor("Light Blue")
        else:
            self.setColor(self.Colour)

#endregion Hex Map

#region Objects
class Object():
    Model = "chessboard_models/pawn" # Placeholder overwritten by subclasses
    def __init__(self, coordinates, colour):
        self.Node = loader().loadModel(self.Model)
        try:
            self.Node.reparentTo(render())
            self.Node.setColor(ape.colour(colour))
            self.Node.setPos(window().getHex(coordinates).Pos)
        except Exception as inst:
            self.Node.removeNode()
            raise inst
        window().getHex(coordinates).content.append(self)
        
    def moveToPos(self,pos):
        self.Node.setPos(pos)
        
    def moveToHex(self,hex:_Hex):
        self.Node.setPos(hex.Pos)
        
    def moveToCoordinates(self,coordinates):
        self.Node.setPos(getHexPos(coordinates))
    
    def __del__(self):
        self.Node.removeNode()


#region piece classes


# Classes for each type of chess piece
# Obviously, we could have done this by just passing a string to Piece's init.
# But if you wanted to make rules for how the pieces move, a good place to start
# would be to make an isValidMove(toHex) method for each piece type (whatever the rules might be on a hex board)
# and then check if the destination square is acceptable during ReleasePiece
class Pawn(Object):
    model = "chessboard_models/pawn"

class King(Object):
    model = "chessboard_models/king"

class Queen(Object):
    model = "chessboard_models/queen"

class Bishop(Object):
    model = "chessboard_models/bishop"

class Knight(Object):
    model = "chessboard_models/knight"

class Rook(Object):
    model = "chessboard_models/rook"
        
#endregion piece classes

#endregion Objects

#region  main


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
        # self.picker.showCollisions(render)
        
class EngineClass(ape.APE):
    def start(self):
        self.base.start()
        self.Scene = HexScene()
        self.Scene.start()
        window().start()

class AppClass(ape.APEApp):
    pass

class MainWindowClass(ape.APELabWindow):#APEWindow):
    def setupUI(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.pandaContainer)
        
        self.genWidget = QtWidgets.QWidget(self)
        genLayout = QtWidgets.QHBoxLayout()
        genLayout.setContentsMargins(0,0,0,0)
        
        #self.genCB = QtWidgets.QCheckBox(self)
        #self.genCB.setText("Use seed 6")
        #genLayout.addWidget(self.genCB)
        self.genButton = AGeWidgets.Button(self,"Regenerate the hex grid",lambda: self.gen())
        genLayout.addWidget(self.genButton)
        
        self.genWidget.setLayout(genLayout)
        layout.addWidget(self.genWidget)
        
        self.cw.setLayout(layout)
        
        self.Console1.setText("self.Pawn = Object((0,0),App().MiscColours[\"Self\"])\n")
    
    def gen(self):
        self.HexGrid.generateHex()
            
    def start(self):
        self.HexGrid = HexGrid()
        
    def getHex(self, i:typing.Tuple[int,int]) -> _Hex:
        return self.HexGrid.getHex(i)

class PandaWidget(ape.PandaWidget):
    pass




#endregion real main
if __name__ == '__main__':
    ape.start(WindowTitle, EngineClass, BaseClass, AppClass, MainWindowClass, PandaWidget, True, SupportsRenderPipeline)
