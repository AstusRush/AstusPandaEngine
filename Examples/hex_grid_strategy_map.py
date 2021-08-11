# This example explores a more advanced hexagonal grid with camera control and pathfinding
#TODO: WIP: Still lacks rotation for moving units
# Author: Robin "Astus" Albers
# Models: Robin "Astus" Albers (hexagon) and Eddie Canaan (cool chess pieces)

SupportsRenderPipeline = False

TRANSPARENT_HEX_RINGS = True

# Python standard imports 1/2
import datetime
import platform

# Print into the console that the program is starting and set the application ID if we are on windows
WindowTitle = "APE-Hex-Grid-Strategy-Map-Example"
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

# Python standard imports 2/2
import sys
sys.path.append('..')
import os
import random
import typing
import weakref
import inspect
import importlib
from heapq import heappush, heappop

# External imports
import numpy as np

# Panda imports
import panda3d as p3d
import panda3d.core as p3dc
import direct as p3dd
from direct.interval.IntervalGlobal import Sequence as p3ddSequence
from direct.showbase.DirectObject import DirectObject
from direct.gui.OnscreenText import OnscreenText
from direct.task.Task import Task

# AGe and APE imports
from AGeLib import *

import AstusPandaEngine as ape
from AstusPandaEngine import engine, base, render, loader
from AstusPandaEngine import window as _window

def window():
    # type: () -> MainWindowClass
    #w:MainWindowClass = _window()
    return _window()#w

sys.path.append('..')

#region Exceptions
class HexException(Exception): pass

class HexOccupiedException(HexException):
    """
    This exception is raised when a hex is already occupied.
    """
    def __init__(self, hex=None):
        # type: (_Hex) -> None
        if hex:
            super().__init__(f"{hex.Name} is already occupied by {hex.Unit.Name}.")
        else:
            super().__init__(f"The hex is already occupied.")

class HexInvalidException(HexException):
    """
    This exception is raised when a hex does not exist.
    """
    def __init__(self, coords:typing.Tuple[int,int] = None):
        if coords:
            super().__init__(f"There is no hex at {coords}.")
        else:
            super().__init__(f"The specified hex does not exist.")
#endregion Exceptions

#region Now we define some helper functions that we will need later

# This function, given a line (vector plus origin point) and a desired z value,
# will give us the point on the line where the desired z value is what we want.
# This is how we know where to position an object in 3D space based on a 2D mouse
# position. It also assumes that we are SelectedHex in the XY plane.
#
# This is derived from the mathematical of a plane, solved for a given point
def PointAtZ(z, point, vec):
    return point + vec * ((z - point.getZ()) / vec.getZ())

# A handy little function for getting the proper position for a given square1
def getHexPos(i:typing.Tuple[int,int]):
    return window().getHex(i).Pos

#endregion helper functions

class HexScene(ape.APEScene):
    # Macro-like function to reduce the amount of code needed to create the
    # onscreen instructions
    def makeStatusLabel(self, i):
        return OnscreenText(
            parent=base().a2dTopLeft, align=p3dc.TextNode.ALeft,
            style=1, fg=(1, 1, 0, 1), shadow=(0, 0, 0, .4),
            pos=(0.06, -0.1 -(.06 * i)), scale=.05, mayChange=True)
    
    def start(self):
        self.Camera = StrategyCamera()
        ape.base().win.setClearColor(p3dc.Vec4(0,0,0,1))
        self.loadSkybox()
        
        # Per-pixel lighting and shadows are initially on
        self.perPixelEnabled = True
        self.shadowsEnabled = True
        
        #base().accept("l", self.togglePerPixelLighting)
        #base().accept("e", self.toggleShadows)

    # Builds the onscreen instruction labels
    def updateStatusLabel(self):
        self.updateLabel(self.lightingPerPixelText, "(l) Per-pixel lighting is", self.perPixelEnabled)
        self.updateLabel(self.lightingShadowsText, "(e) Shadows are", self.shadowsEnabled)
    
    # Appends either (on) or (off) to the base string based on the base value
    def updateLabel(self, obj, base, var):
        if var:
            s = " (on)"
        else:
            s = " (off)"
        obj.setText(base + s)
    
    # This function turns per-pixel lighting on or off.
    def togglePerPixelLighting(self):
        if self.perPixelEnabled:
            self.perPixelEnabled = False
            if self.shadowsEnabled:
                self.shadowsEnabled = False
                self.light.setShadowCaster(False)
                #  self.light2.setShadowCaster(False)
            render().clearShader()
        else:
            self.perPixelEnabled = True
            render().setShaderAuto()
        self.updateStatusLabel()

    # This function turns shadows on or off.
    def toggleShadows(self):
        if self.shadowsEnabled:
            self.shadowsEnabled = False
            self.light.setShadowCaster(False)
            #  self.light2.setShadowCaster(False)
        else:
            if not self.perPixelEnabled:
                self.togglePerPixelLighting()
            self.shadowsEnabled = True
            self.light.setShadowCaster(True, 1024, 1024)
            #  self.light2.setShadowCaster(True, 1024, 1024)
        self.updateStatusLabel()
        
    def loadSkybox(self):
        self.Camera.loadSkybox()

class StrategyCamera():
    def __init__(self):
        ape.base().win.setClearColor(p3dc.Vec4(0,0,0,1))
        self.Plane = p3dc.Plane(p3dc.Vec3(0, 0, 1), p3dc.Point3(0, 0, 0))
        
        self.SpaceSkyBoxCentre = None
        self.SpaceSkyBox = None
        
        self.CameraCenter = p3dc.NodePath(p3dc.PandaNode("CameraCenter"))
        self.CameraCenter.reparentTo(ape.render())
        self.CameraCenter.setPos(p3dc.Vec3(0,0,0))
        self.CameraRotCenter = p3dc.NodePath(p3dc.PandaNode("CameraRotCenter"))
        self.CameraRotCenter.reparentTo(self.CameraCenter)
        self.CameraRotCenter.setPos(p3dc.Vec3(0,0,0))
        self.CameraRotCenter.setP(-45)
        ape.base().camera.reparentTo(self.CameraRotCenter)
        ape.base().camera.setPos(0,-15,0)
        ape.base().camera.lookAt(self.CameraCenter)
        
        self.LimitX: typing.Tuple[float,float] = (float("-inf"), float("inf"))
        self.LimitY: typing.Tuple[float,float] = (float("-inf"), float("inf"))
        
        self.SmoothCam = False
        self.CamMouseControl = False
        self.CamMouseControlRotate = False
        self.CamMouseControlCentre = p3dc.Vec3(0,0,0)
        self.mouseTask = base().taskMgr.add(lambda task: self._mouseTask(task), 'mouseTask')
        
        self.KeyMap = {"cam-left":0, "cam-right":0, "cam-forward":0, "cam-backward":0, "cam-rot-left":0, "cam-rot-right":0}
        self.acceptAllCombinations("a", self.setKey, ["cam-left",1])
        self.acceptAllCombinations("d", self.setKey, ["cam-right",1])
        self.acceptAllCombinations("w", self.setKey, ["cam-forward",1])
        self.acceptAllCombinations("s", self.setKey, ["cam-backward",1])
        self.acceptAllCombinations("arrow_left", self.setKey, ["cam-left",1])
        self.acceptAllCombinations("arrow_right", self.setKey, ["cam-right",1])
        self.acceptAllCombinations("arrow_up", self.setKey, ["cam-forward",1])
        self.acceptAllCombinations("arrow_down", self.setKey, ["cam-backward",1])
        self.acceptAllCombinations("a-up", self.setKey, ["cam-left",0])
        self.acceptAllCombinations("d-up", self.setKey, ["cam-right",0])
        self.acceptAllCombinations("w-up", self.setKey, ["cam-forward",0])
        self.acceptAllCombinations("s-up", self.setKey, ["cam-backward",0])
        self.acceptAllCombinations("arrow_left-up", self.setKey, ["cam-left",0])
        self.acceptAllCombinations("arrow_right-up", self.setKey, ["cam-right",0])
        self.acceptAllCombinations("arrow_up-up", self.setKey, ["cam-forward",0])
        self.acceptAllCombinations("arrow_down-up", self.setKey, ["cam-backward",0])
        self.acceptAllCombinations("q", self.setKey, ["cam-rot-left",1])
        self.acceptAllCombinations("e", self.setKey, ["cam-rot-right",1])
        self.acceptAllCombinations("q-up", self.setKey, ["cam-rot-left",0])
        self.acceptAllCombinations("e-up", self.setKey, ["cam-rot-right",0])
        
        base().taskMgr.add(lambda task: self.moveCamera(task), "moveCamereTask")
        self.acceptAllCombinations("wheel_up",   lambda: self.zoomCamera(-1))
        self.acceptAllCombinations("wheel_down", lambda: self.zoomCamera(+1))
        base().accept("mouse2",    lambda: self.setCamMouseControl(True,False,False)) # MMB
        base().accept("mouse2-up", lambda: self.setCamMouseControl(False,False,False)) # MMB
        base().accept("shift-mouse2",    lambda: self.setCamMouseControl(True,False,True)) # shift + MMB
        #base().accept("shift-mouse2-up", lambda: self.setCamMouseControl(False,False,True)) # shift + MMB
        base().accept("control-mouse2",    lambda: self.setCamMouseControl(True,True,False)) # ctrl + MMB
        #base().accept("control-mouse2-up", lambda: self.setCamMouseControl(False,True,False)) # ctrl + MMB #VALIDATE: Is this triggered when either key is released?
        base().accept("alt-mouse2",    lambda: self.setCamMouseControl(True,True,True)) # alt + MMB
        #base().accept("alt-mouse2-up", lambda: self.setCamMouseControl(False,True,True)) # alt + MMB #VALIDATE: Is this triggered when either key is released?
        
        
    def loadSkybox(self):
        if self.SpaceSkyBox:
            self.SpaceSkyBox.removeNode()
        if self.SpaceSkyBoxCentre:
            self.SpaceSkyBoxCentre.removeNode()
        size = 500
        self.SpaceSkyBoxCentre = p3dc.NodePath(p3dc.PandaNode("SpaceSkyBoxCentre"))
        self.SpaceSkyBoxCentre.reparentTo(ape.render())
        self.SpaceSkyBox = loader().loadModel('Skybox Textures/Green Space 1/GreenSpace1.egg')
        self.SpaceSkyBox.setScale(size)
        self.SpaceSkyBox.setBin('background', 0)
        self.SpaceSkyBox.setDepthWrite(0)
        self.SpaceSkyBox.setTwoSided(True)
        self.SpaceSkyBox.setTexGen(p3dc.TextureStage.getDefault(),p3dc.TexGenAttrib.MWorldCubeMap)
        self.SpaceSkyBox.reparentTo(self.SpaceSkyBoxCentre)
        self.SpaceSkyBox.setPos((-size/2,-size/2,-size/2))
        
    def acceptAllCombinations(self, key, *args):
        base().accept(key, *args)
        base().accept("control-"+key, *args)
        base().accept("alt-"+key, *args)
        base().accept("shift-"+key, *args)
        
    def setLimits(self, limitX: typing.Tuple[float,float], limitY: typing.Tuple[float,float]):
        self.LimitX = (min(limitX),max(limitX))
        self.LimitY = (min(limitY),max(limitY))
        
    def _enforceLimits(self):
        if   self.CameraCenter.getX() < self.LimitX[0]:
            self .CameraCenter.setX(    self.LimitX[0])
        elif self.CameraCenter.getX() > self.LimitX[1]:
            self .CameraCenter.setX(    self.LimitX[1])
        if   self.CameraCenter.getY() < self.LimitY[0]:
            self .CameraCenter.setY(    self.LimitY[0])
        elif self.CameraCenter.getY() > self.LimitY[1]:
            self .CameraCenter.setY(    self.LimitY[1])
        self.SpaceSkyBoxCentre.setPos(self.CameraCenter.getPos())
    
    def setKey(self, key, value):
        """Records the state of camera movement keys"""
        self.KeyMap[key] = value
    
    def moveCamera(self, task): #TODO: Make limits that can then be set by HexGrid to limit the camera to the relevant area
        if (self.KeyMap["cam-rot-left"]!=0):
            self.CameraCenter.setH(self.CameraCenter, +100 * p3dc.ClockObject.getGlobalClock().getDt())
        if (self.KeyMap["cam-rot-right"]!=0):
            self.CameraCenter.setH(self.CameraCenter, -100 * p3dc.ClockObject.getGlobalClock().getDt())
        if (self.KeyMap["cam-forward"]!=0):
            self.CameraCenter.setY(self.CameraCenter, + 20 * p3dc.ClockObject.getGlobalClock().getDt())
        if (self.KeyMap["cam-backward"]!=0):
            self.CameraCenter.setY(self.CameraCenter, - 20 * p3dc.ClockObject.getGlobalClock().getDt())
        if (self.KeyMap["cam-right"]!=0):
            self.CameraCenter.setX(self.CameraCenter, + 20 * p3dc.ClockObject.getGlobalClock().getDt())
        if (self.KeyMap["cam-left"]!=0):
            self.CameraCenter.setX(self.CameraCenter, - 20 * p3dc.ClockObject.getGlobalClock().getDt())
        self._enforceLimits()
        return task.cont
    
    def zoomCamera(self, sign): #TODO: Support zoom-to-cursor and use it as a standard as it feels way more intuitive. Make a flag (as a member) that governs this behaviour
        y = -ape.base().camera.getY() + sign*5
        if y > 100: y = 100
        elif y < 5: y = 5
        ape.base().camera.setY(-y)
        ape.base().camera.lookAt(self.CameraCenter)
    
    def setCamMouseControl(self, active, rotate, smooth):
        self.SmoothCam = smooth
        if active and base().mouseWatcherNode.hasMouse():
            mpos = tuple(base().mouseWatcherNode.getMouse())
            if rotate or self.SmoothCam:
                self.CamMouseControl = True
                self.CamMouseControlRotate = rotate
                self.CamMouseControlCentre = mpos
            else:
                self.CamMouseControlRotate = False
                pos3d = p3dc.Point3()
                nearPoint = p3dc.Point3()
                farPoint = p3dc.Point3()
                base().camLens.extrude(mpos, nearPoint, farPoint)
                if self.Plane.intersectsLine(
                        pos3d,
                        render().getRelativePoint(ape.base().camera, nearPoint),
                        render().getRelativePoint(ape.base().camera, farPoint)
                        ):
                    self.CamMouseControl = True
                    self.CamMouseControlCentre = pos3d
                else:
                    self.CamMouseControl = False
        else:
            self.CamMouseControl = False
            self.CamMouseControlRotate = False
    
    def _mouseTask(self, task):
        # Check to see if we can access the mouse. We need it to do anything else
        if base().mouseWatcherNode.hasMouse() and self.CamMouseControl:
            mpos = base().mouseWatcherNode.getMouse()
            if self.CamMouseControlRotate:
                if self.SmoothCam:
                    d = (mpos - self.CamMouseControlCentre)
                    self.CameraCenter.setH(self.CameraCenter, 10*d[0])
                    p = self.CameraRotCenter.getP() + 10*d[1]
                    if p < -90: p = -90
                    elif p > 90: p = 90
                    self.CameraRotCenter.setP(p)
                else:
                    d = (mpos - self.CamMouseControlCentre)
                    self.CameraCenter.setH(self.CameraCenter, 100*d[0])
                    p = self.CameraRotCenter.getP() + 100*d[1]
                    if p < -90: p = -90
                    elif p > 90: p = 90
                    self.CameraRotCenter.setP(p)
                    self.CamMouseControlCentre = tuple(mpos)
            else:
                if self.SmoothCam:
                    d = (mpos - self.CamMouseControlCentre)
                    self.CameraCenter.setX(self.CameraCenter, 0.5*d[0])
                    self.CameraCenter.setY(self.CameraCenter, 0.5*d[1])
                else:
                    pos3d = p3dc.Point3()
                    nearPoint = p3dc.Point3()
                    farPoint = p3dc.Point3()
                    base().camLens.extrude(mpos, nearPoint, farPoint)
                    if self.Plane.intersectsLine(
                            pos3d,
                            render().getRelativePoint(ape.base().camera, nearPoint),
                            render().getRelativePoint(ape.base().camera, farPoint)
                            ):
                        self.CameraCenter.setPos(self.CameraCenter.getPos()+self.CamMouseControlCentre-pos3d)
                self._enforceLimits()
        
        return Task.cont

#region Hex Map
class HexGrid():
    #TODO: Write a method that checks if given coordinates exist i.e. if they lie within the grid and use it in getHex
    def __init__(self, scene:ape.APEScene=None, root:p3dc.NodePath = None, size: typing.Tuple[int,int] = (50,50)) -> None:
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
        self.HighlightedHex = False # type: _Hex
        # This wil represent the index of the hex where currently dragged piece was grabbed from
        self.SelectedHex = False # type: _Hex
        
        # Start the task that handles the picking
        self.mouseTask = base().taskMgr.add(self._mouseTask, 'mouseTask')
        
        base().accept("mouse1", lambda: self._selectHighlightedHex()) # LMB
        base().accept("mouse3", lambda: self._interactWithHighlightedHex()) # RMB
        
    def clearHexes(self):
        self.HighlightedHex = False # type: _Hex
        self.SelectedHex = False # type: _Hex
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
                l.append(_Hex(self, self.Scene, self.Root, f"Hex ({i},{j})", (i,j), (y,x,0), "Blue"))
            self.Hexes.append(l)
            
    def getHex(self, i):
        # type: ( typing.Union[typing.Tuple[int,int], typing.Tuple[int,int,int]] ) -> _Hex
        if len(i) == 3:
            i = self.cubeToCoord(i)
        if len(i) == 2:
            i = ( int(i[0]) , int(i[1]) )
        else:
            raise HexInvalidException(i)
        if self._isValidCoordinate(i):
            return self.Hexes[int(i[0])][int(i[1])]
        else:
            raise HexInvalidException(i)
            
    def _isValidCoordinate(self, i):
        # type: ( typing.Union[typing.Tuple[int,int], typing.Tuple[int,int,int]] ) -> bool
        if len(i) == 3:
            i = self.cubeToCoord(i)
        if len(i) != 2:
            return False
        if i[0] < 0 or i[0] >= len(self.Hexes):
            return False
        if i[1] < 0 or i[1] >= len(self.Hexes[i[0]]):
            return False
        return True
    
    def cubeToCoord(self, cube:typing.Tuple[int,int,int]) -> typing.Tuple[int,int]:
        col = cube[0]
        row = cube[2] + (cube[0] - (cube[0]&1)) / 2
        return (col, row)
    
    def coordToCube(self, coord:typing.Tuple[int,int]) -> typing.Tuple[int,int,int]:
        x = coord[0]
        z = coord[1] - (coord[0] - (coord[0]&1)) / 2
        y = -x-z
        return (int(x), int(y), int(z))
    
  #region Interaction
    def _mouseTask(self, task):
        # This task deals with the highlighting and SelectedHex based on the mouse
        
        # First, clear the current highlight
        if self.HighlightedHex is not False:
            self.HighlightedHex.highlight(False)
            self.HighlightedHex = False
        
        # Check to see if we can access the mouse. We need it to do anything else
        if base().mouseWatcherNode.hasMouse():
            # get the mouse position
            mpos = base().mouseWatcherNode.getMouse()
            
            # Set the position of the ray based on the mouse position
            base().pickerRay.setFromLens(base().camNode, mpos.getX(), mpos.getY())
            
            # If we are SelectedHex something, set the position of the object
            # to be at the appropriate point over the plane of the board
            if self.SelectedHex is not False:
                # Gets the point described by pickerRay.getOrigin(), which is relative to
                # camera, relative instead to render
                nearPoint = render().getRelativePoint( base().camera, base().pickerRay.getOrigin() )
                # Same thing with the direction of the ray
                nearVec  = render().getRelativeVector( base().camera, base().pickerRay.getDirection() )
                #for i in self.SelectedHex.content:
                #    i.Node.setPos( PointAtZ(.5, nearPoint, nearVec) )
            
            # Do the actual collision pass (Do it only on the squares for efficiency purposes)
            base().picker.traverse(self.Root)
            if base().pq.getNumEntries() > 0:
                # if we have hit something, sort the hits so that the closest is first, and highlight that node
                base().pq.sortEntries()
                i:str = base().pq.getEntry(0).getIntoNode().getTag('hex')
                i = self.getHex((int(i.split(" ")[0]), int(i.split(" ")[1]))) # type: _Hex
                # Set the highlight on the picked square
                i.highlight()
                self.HighlightedHex = i
                window().Statusbar.showMessage(i.Name)
        
        return Task.cont
    
    def _selectHighlightedHex(self):
        if self.SelectedHex is not False:
            if self.SelectedHex is self.HighlightedHex:
                self.SelectedHex.select(False)
                self.SelectedHex.highlight()
                self.SelectedHex = False
                return
            else:
                self.SelectedHex.select(False)
                self.SelectedHex = False
        if self.HighlightedHex is not False:
            self.SelectedHex = self.HighlightedHex
            self.SelectedHex.select()
            self.HighlightedHex = False
    
    def _interactWithHighlightedHex(self):
        if self.SelectedHex is not False and self.HighlightedHex is not False:
            if self.SelectedHex.moveUnitToHex(self.HighlightedHex):
                self._selectHighlightedHex()
  #endregion Interaction

class _Hex():
    SELECT_COLOUR = "Yellow"
    HIGHLIGHT_COLOUR = "Light Blue"
    def __init__(self, grid:HexGrid, scene:ape.APEScene, root, name:str, coordinates:typing.Tuple[int,int], pos:typing.Tuple[int,int,int], colour: str):
        try:
            # What we need:
            # - A hexagonal mesh for the click-detection and to highlight the hex
            # - A Hexagonal ring to highlight the edges of all hexes
            # - These two meshes must be as simple as possible but must be able to be visible, blink, and be hidden independently of one another
            #
            self.Name = name
            self.Colour = colour
            self.CurrentColour = colour
            self.Coordinates = coordinates
            self.grid = weakref.ref(grid)
            
            # Save cube coordinates
            self.CubeCoordinates = grid.coordToCube(coordinates)
            
            self.Pos = p3dc.LPoint3(pos)
            mesh = "simple_models/hexagon.ply"
            meshRing = "simple_models/hexagonRing.ply"
            # Load, parent, colour, and position the model (a hexagon-shaped ring consisting of 6 polygons)
            self.Model = loader().loadModel(meshRing)
            self.Model.reparentTo(root)
            self.Model.setPos(self.Pos)
            if TRANSPARENT_HEX_RINGS:
                self.Model.setTransparency(p3dc.TransparencyAttrib.MAlpha)
            self.setColor(self.Colour)
            # Load, parent, hide, and position the face (a single hexagon polygon)
            self.Face = loader().loadModel(mesh)
            self.Face.reparentTo(self.Model)
            self.Face.setPos(p3dc.LPoint3((0,0,-0.01)))
            self.setColorFace("Light Blue")
            #TODO: Make transparrent
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
            self.Unit = None # type: Unit
            self.Navigable = True
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
            
    def moveUnitToHex(self,other):
        # type: (_Hex) -> bool
        return self.Unit.moveTo(other)
        #if self.Unit and not other.Unit:
        #    self.Unit.moveToHex(other)
        #    other.Unit = self.Unit
        #    self.Unit = None
        #    return True
        #else:
        #    return False
    
    def setColor(self, colour, alpha = 0.2):
        if isinstance(colour,str):
            colour = App().PenColours[colour].color()
            colour.setAlphaF(alpha)
        self.Model.setColor(ape.colour(colour))
    
    def setColorFace(self, colour, alpha = 0.2):
        if isinstance(colour,str):
            colour = App().PenColours[colour].color()
            colour.setAlphaF(alpha)
        self.Face.setColor(ape.colour(colour))
        
    def highlight(self, highlight:bool = True):
        if highlight:
            if TRANSPARENT_HEX_RINGS:
                self.Model.setTransparency(p3dc.TransparencyAttrib.MNone)
            self.setColor(self.HIGHLIGHT_COLOUR)
        else:
            if TRANSPARENT_HEX_RINGS and not self.CurrentColour == self.SELECT_COLOUR:
                self.Model.setTransparency(p3dc.TransparencyAttrib.MAlpha)
            self.setColor(self.CurrentColour)
        
    def select(self, select:bool = True):
        if select:
            self.CurrentColour = self.SELECT_COLOUR
            if TRANSPARENT_HEX_RINGS:
                self.Model.setTransparency(p3dc.TransparencyAttrib.MNone)
            self.setColor(self.SELECT_COLOUR)
            self.Face.setTransparency(p3dc.TransparencyAttrib.MAlpha)
            self.Face.show()
        else:
            self.CurrentColour = self.Colour
            if TRANSPARENT_HEX_RINGS:
                self.Model.setTransparency(p3dc.TransparencyAttrib.MAlpha)
            self.setColor(self.Colour)
            self.Face.setTransparency(p3dc.TransparencyAttrib.MNone)
            self.Face.hide()
            
    def getNeighbour(self,direction=-1):
        """
        Returns the specified neighbour in direction if 0<=direction<=5 or else all neighbours. \n
        Raises HexInvalidException if the specified neighbour does not exist (which can happen if this hex is at the edge of the map).
        """
        if 0 <= direction and direction <= 5:
            return self.grid().getHex( [a+b for a,b in zip(self.CubeCoordinates, [
                    (+1, -1, 0), (+1, 0, -1), (0, +1, -1),
                    (-1, +1, 0), (-1, 0, +1), (0, -1, +1),
                ][direction])])
        else:
            l = []
            for i in [
                        (+1, -1, 0), (+1, 0, -1), (0, +1, -1),
                        (-1, +1, 0), (-1, 0, +1), (0, -1, +1),
                    ]:
                try:
                    l.append(self.grid().getHex([a+b for a,b in zip(self.CubeCoordinates, i)]))
                except HexInvalidException:
                    pass
            return l
    
    def distance(self, other):
        """
        Returns the distance in number of hexagon steps.
        """
        x1, y1, z1 = self.CubeCoordinates
        x2, y2, z2 = other.CubeCoordinates if isinstance(other, _Hex) else other
        return max(abs(x1 - x2), abs(y1 - y2), abs(z1 - z2))
        
    def __lt__(self, other):
        # type: (_Hex) -> bool
        return self.CubeCoordinates < other.CubeCoordinates

def findPath(start:_Hex, destination:_Hex, navigable = lambda hex: hex.Navigable, cost = lambda hex: 1) -> typing.List[_Hex]:
    """
    The hex path finder. \n
    Returns a list containing the hexes that form a shortest path between start and destination (including destination but excluding start). \n
    start       : Starting hex for path finding. \n
    destination : Destination hex for path finding. \n
    navigable   : A function that, given a _Hex, tells us whether we can move through this hex. \n
    cost        : A cost function for moving through a hex. Should return a value >= 1. By default all costs are 1. \n
    """
    Found = False
    Done = False
    Path: typing.List[_Hex] = None
    Closedset = set()
    Openset = [(destination.distance(start), 0, start, ())]
    
    def _compute_path(path):
        result = []
        while path:
            pos, path = path
            result.append(pos)
        return result[::-1]
    
    while not Done:
        for i in range(100):
            if not Openset:
                Done = True
                break
            h, cur_cost, pos, path = heappop(Openset)
            if pos in Closedset:
                continue
            new_path = (pos, path)
            if pos == destination:
                Path = _compute_path(new_path)
                Found = Done = True
                del Openset[:]
                break
            Closedset.add(pos)
            for new_pos in pos.getNeighbour():
                if (not navigable(new_pos)) or (new_pos in Closedset):
                    continue
                new_cost = cur_cost + cost(new_pos)
                new_h = new_cost + destination.distance(new_pos)
                heappush(Openset, (new_h, new_cost, new_pos, new_path))
    try:
        if len(Path) > 1:
            return Path[1:]
        else:
            return []
    except:
        return []

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
        self.setPos(pos)
        
    def moveToHex(self,hex:_Hex):
        self.setPos(hex.Pos)
        
    def moveToCoordinates(self,coordinates):
        self.setPos(getHexPos(coordinates))
        
    def setPos(self, pos):
        self.Node.lookAt(pos)
        self.Node.posInterval(pos,min(6,abs(sum(self.Node.getPos()-pos))))
    
    def __del__(self):
        self.Node.removeNode()
        
class Unit():
    def __init__(self, coordinates, colour, name="a Unit", model="chessboard_models/knight"):
        self.Model = model
        self.Name = name
        self.hex: weakref.ref[_Hex] = None
        self.Node = loader().loadModel(self.Model)
        self.BaseMovePoints = float("inf") #10
        self.MovePoints = self.BaseMovePoints
        try:
            self.Node.reparentTo(render())
            self.Node.setColor(ape.colour(colour))
            self.moveToCoordinates(coordinates)
        except Exception as inst:
            self.Node.removeNode()
            raise inst
        
    #def moveToPos(self,pos):
    #    self.Node.setPos(pos)
    
    def __del__(self):
        self.Node.removeNode()
        
    def endTurn(self):
        pass
    
    def beginTurn(self):
        self.MovePoints = self.BaseMovePoints
        
    def moveToHex(self, hex:_Hex, animate= True):
        self.Coordinates = hex.Coordinates
        if hex.Unit:
            raise HexOccupiedException(hex)
        else:
            if animate and self.hex:
                self.Node.lookAt(hex.Pos)
                #time = min(6, np.sqrt(sum([i**2 for i in list(self.Node.getPos()-hex.Pos)])) )/6
                time = min(6, self.hex().distance(hex) )/6
                self.Node.posInterval(time, hex.Pos).start()
            else:
                self.Node.setPos(hex.Pos)
            hex.Unit = self
            self.hex = weakref.ref(hex)
            
    def _navigable(self, hex:_Hex):
        return (not bool(hex.Unit)) and hex.Navigable
        
    def _tileCost(self, hex:_Hex):
        return 1
            
    def moveTo(self, hex:_Hex):
        if not self._navigable(hex):
            return False
        else:
            path = findPath(self.hex(), hex, self._navigable, self._tileCost)
            if not path or len(path)>self.MovePoints:
                return False
            else:
                seq = p3ddSequence(name = self.Name+" move")
                for i in path:
                    seq.append( self.Node.posInterval(0.5, i.Pos) ) #, startPos=Point3(0, 10, 0)))
                
                seq.start()
                self.hex().Unit = None
                hex.Unit = self
                self.hex = weakref.ref(hex)
                self.Coordinates = hex.Coordinates
                self.MovePoints -= len(path)
                return True
        
    def moveToCoordinates(self,coordinates):
        self.moveToHex(window().getHex(coordinates))


#region piece classes
# Classes for each type of chess piece
# Obviously, we could have done this by just passing a string to Piece's init.
# But if you wanted to make rules for how the pieces move, a good place to start
# would be to make an isValidMove(toSquare) method for each piece type
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


# Function to put instructions on the screen.
def addInstructions(pos, msg):
    return OnscreenText(text = msg, style = 1, fg = (1, 1, 1, 1), 
                        pos = (-0.9, pos - 0.2), align = p3dc.TextNode.ALeft, scale = .035)

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
        
        self.Console1.setText("self.Pawn = Unit((0,0),App().MiscColours[\"Self\"])\n")
    
    def gen(self):
        self.HexGrid.generateHex()
            
    def start(self):
        self.HexGrid = HexGrid()
        Unit((25,25),App().MiscColours["Self"],name="self",model="chessboard_models/knight")
        Unit((27,22),App().MiscColours["Neutral"],name="a pawn",model="chessboard_models/pawn")
        Unit((26,23),App().MiscColours["Neutral"],name="a pawn",model="chessboard_models/pawn")
        Unit((25,23),App().MiscColours["Neutral"],name="a pawn",model="chessboard_models/pawn")
        Unit((24,23),App().MiscColours["Neutral"],name="a pawn",model="chessboard_models/pawn")
        Unit((23,22),App().MiscColours["Neutral"],name="a pawn",model="chessboard_models/pawn")
        
    def getHex(self, i:typing.Tuple[int,int]) -> _Hex:
        return self.HexGrid.getHex(i)

class PandaWidget(ape.PandaWidget):
    pass




#endregion real main
if __name__ == '__main__':
    ape.start(WindowTitle, EngineClass, BaseClass, AppClass, MainWindowClass, PandaWidget, True, SupportsRenderPipeline)
