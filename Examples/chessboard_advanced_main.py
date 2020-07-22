#!/usr/bin/env python

# Author: Robin Albers
# Models: Eddie Canaan
# Authors of basic Version: Shao Zhang and Phil Saltzman
# Last Updated: 2020-07-22
#
# This tutorial shows how to determine what objects the mouse is pointing to.
# We do this using a collision ray that extends from the mouse position and points straight into the scene, and see what it collides with.
# We pick the object with the closest collision.
# This advanced version is structured more reasonable, shadows are added and the camera can cycle to different locations.
# REMINDER: add info about what the advanced version does

#TODO: rework the entire code and make it readable
#TODO: add scenery around the chess board
#MAYBE: add chess stuff like defeating enemies by moving on top of them
#MAYBE: add 1st/3rd Person movement?
#MAYBE: add toggleable chess movement rules?

import datetime
import platform
WindowTitle = "APE-Chessboard-Advanced-Example"
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
import sys
sys.path.append('..')

# Panda imports
import panda3d as p3d
import panda3d.core as p3dc
from direct.showbase.ShowBase import ShowBase
from direct.showbase.DirectObject import DirectObject
from direct.gui.OnscreenText import OnscreenText
from direct.task.Task import Task

# AGE and APE imports
import AGeLib as age # pylint: disable=import-error
from AGeLib import NC # pylint: disable=import-error

import AstusPandaEngine as ape # pylint: disable=import-error
from AstusPandaEngine import window, engine, base, render, loader # pylint: disable=import-error

# Qt imports
from PyQt5.QtCore import pyqtProperty, pyqtSignal, qFuzzyCompare, QObject, QPropertyAnimation # pylint: disable=no-name-in-module
from PyQt5.QtGui import QMatrix4x4, QQuaternion, QVector3D # pylint: disable=no-name-in-module
from PyQt5 import QtWidgets,QtCore,QtGui,Qt , Qt3DAnimation,Qt3DCore,Qt3DExtras,Qt3DInput,Qt3DLogic,Qt3DRender , QtQml
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView,QWebEngineSettings # pylint: disable=no-name-in-module
except:
    from PyQtWebEngine.QtWebEngineWidgets import QWebEngineView,QWebEngineSettings


#
#region First we define some constants for the colors
BLACK = (0, 0, 0, 1)
WHITE = (1, 1, 1, 1)
HIGHLIGHT = (0, 1, 1, 1)
PIECEBLACK = (.15, .15, .15, 1)
#endregion constants

#region Now we define some helper functions that we will need later

# This function, given a line (vector plus origin point) and a desired z value,
# will give us the point on the line where the desired z value is what we want.
# This is how we know where to position an object in 3D space based on a 2D mouse
# position. It also assumes that we are dragging in the XY plane.
#
# This is derived from the mathematical of a plane, solved for a given point
def PointAtZ(z, point, vec):
    return point + vec * ((z - point.getZ()) / vec.getZ())

# A handy little function for getting the proper position for a given square1
def SquarePos(i):
    return p3dc.LPoint3((i % 8) - 3.5, int(i // 8) - 3.5, 0)

# Helper function for determining whether a square should be white or black
# The modulo operations (%) generate the every-other pattern of a chess-board
def SquareColour(i):
    if (i + ((i // 8) % 2)) % 2:
        return BLACK
    else:
        return WHITE
#endregion helper functions

##

class ChessScene(ape.APEScene):
    # Macro-like function to reduce the amount of code needed to create the
    # onscreen instructions
    def makeStatusLabel(self, i):
        return OnscreenText(
            parent=base().a2dTopLeft, align=p3dc.TextNode.ALeft,
            style=1, fg=(1, 1, 0, 1), shadow=(0, 0, 0, .4),
            pos=(0.06, -0.1 -(.06 * i)), scale=.05, mayChange=True)

    def start(self):
        self.setupLights()  # Setup default lighting

        # Now we create the chess board and its pieces

        # We will attach all of the squares to their own root. This way we can do the
        # collision pass just on the squares and save the time of checking the rest of the scene
        self.squareRoot = render().attachNewNode("squareRoot")
        self.squareRoot.setPos((0,0,0))

        # For each square
        self.squares = [None for i in range(64)]
        self.pieces = [None for i in range(64)]
        for i in range(64):
            # Load, parent, colour and position the model (a single square polygon)
            self.squares[i] = loader().loadModel("chessboard_models/square")
            self.squares[i].reparentTo(self.squareRoot)
            self.squares[i].setPos(SquarePos(i))
            self.squares[i].setColor(SquareColour(i))
            # Set the model itself to be collideable with the ray. If this model was
            # any more complex than a single polygon, you should set up a collision
            # sphere around it instead. But for single polygons this works fine.
            self.squares[i].find("**/polygon").node().setIntoCollideMask(p3dc.BitMask32.bit(1))
            # Set a tag on the square's node so we can look up what square this is later during the collision pass
            self.squares[i].find("**/polygon").node().setTag('square', str(i))
            # We will use this variable as a pointer to whatever piece is currently in this square
        
        
        # The order of pieces on a chessboard from white's perspective. This list
        # contains the constructor functions for the piece classes defined below
        pieceOrder = (Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook)
        
        for i in range(8, 16):
            # Load the white pawns
            self.pieces[i] = Pawn(i, WHITE)
        for i in range(48, 56):
            # load the black pawns
            self.pieces[i] = Pawn(i, PIECEBLACK)
        for i in range(8):
            # Load the special pieces for the front row and colour them white
            self.pieces[i] = pieceOrder[i](i, WHITE)
            # Load the special pieces for the back row and colour them black
            self.pieces[i + 56] = pieceOrder[i](i + 56, PIECEBLACK)
        
        # This will represent the index of the currently highlighted square
        self.hiSq = False
        # This wil represent the index of the square where currently dragged piece was grabbed from
        self.dragging = False

        # Per-pixel lighting and shadows are initially on
        self.perPixelEnabled = True
        self.shadowsEnabled = True
        # This code puts the standard title and instruction text on screen
        self.mouseText = self.makeStatusLabel(0)
        self.mouseText.setText("Left-click and drag: Pick up and drag piece")
        self.spaceText = self.makeStatusLabel(1)
        self.spaceText.setText("SPACE: Cycle camera positions")
        self.lightingPerPixelText = self.makeStatusLabel(2)
        self.lightingShadowsText = self.makeStatusLabel(3)

        # Finally call the function that builds the instruction texts
        self.updateStatusLabel()
        
        # Start the task that handles the picking
        self.mouseTask = base().taskMgr.add(self._mouseTask, 'mouseTask')
        base().accept("mouse1", self.grabPiece)  # left-click grabs a piece
        base().accept("mouse1-up", self.releasePiece)  # releasing places it
        self.nextCamPos = 1
        base().accept("space", self.toggleCam)  # releasing places it
        base().accept("l", self.togglePerPixelLighting)
        base().accept("e", self.toggleShadows)

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

    # This function swaps the positions of two pieces
    def swapPieces(self, fr, to):
        temp = self.pieces[fr]
        self.pieces[fr] = self.pieces[to]
        self.pieces[to] = temp
        if self.pieces[fr]:
            self.pieces[fr].square = fr
            self.pieces[fr].obj.setPos(SquarePos(fr))
        if self.pieces[to]:
            self.pieces[to].square = to
            self.pieces[to].obj.setPos(SquarePos(to))

    def _mouseTask(self, task):
        # This task deals with the highlighting and dragging based on the mouse

        # First, clear the current highlight
        if self.hiSq is not False:
            self.squares[self.hiSq].setColor(SquareColour(self.hiSq))
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
                nearPoint = render().getRelativePoint(
                    base().camera, base().pickerRay.getOrigin())
                # Same thing with the direction of the ray
                nearVec = render().getRelativeVector(
                    base().camera, base().pickerRay.getDirection())
                self.pieces[self.dragging].obj.setPos(
                    PointAtZ(.5, nearPoint, nearVec))

            # Do the actual collision pass (Do it only on the squares for efficiency purposes)
            base().picker.traverse(self.squareRoot)
            if base().pq.getNumEntries() > 0:
                # if we have hit something, sort the hits so that the closest is first, and highlight that node
                base().pq.sortEntries()
                i = int(base().pq.getEntry(0).getIntoNode().getTag('square'))
                # Set the highlight on the picked square
                self.squares[i].setColor(HIGHLIGHT)
                self.hiSq = i

        return Task.cont

    def grabPiece(self):
        # If a square is highlighted and it has a piece, set it to dragging mode
        if self.hiSq is not False and self.pieces[self.hiSq]:
            self.dragging = self.hiSq
            self.hiSq = False

    def releasePiece(self):
        # Letting go of a piece. If we are not on a square, return it to its original
        # position. Otherwise, swap it with the piece in the new square
        # Make sure we really are dragging something
        if self.dragging is not False:
            # We have let go of the piece, but we are not on a square
            if self.hiSq is False:
                self.pieces[self.dragging].obj.setPos(SquarePos(self.dragging))
            else:
                # Otherwise, swap the pieces
                self.swapPieces(self.dragging, self.hiSq)

        # We are no longer dragging anything
        self.dragging = False

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

    def setupLights(self):  # This function sets up some default lighting with simple shadows
        #ambientLight = p3dc.AmbientLight("ambientLight")
        #ambientLight.setColor((.8, .8, .8, 1))
        #directionalLight = p3dc.DirectionalLight("directionalLight")
        #directionalLight.setDirection(p3dc.LVector3(0, 45, -45))
        #directionalLight.setColor((0.2, 0.2, 0.2, 1))
        #render().setLight(render().attachNewNode(directionalLight))
        #render().setLight(render().attachNewNode(ambientLight))
        
        # Shadows
        self.light = p3dc.Spotlight("Spot")
        self.light_node = render().attachNewNode(self.light) # generates instance of p3dc.NodePath
        print("self.light_node",type(self.light_node))
        self.light.setScene(render())
        self.light.setShadowCaster(True, 1024, 1024)#.setShadowCaster(True)
        #self.light.showFrustum()
        # This exponent value sets how soft the edge of the spotlight is.
        # 0 means a hard edge. 128 means a very soft edge.
        #self.light.setExponent(60.0)
        # Attenuation controls how the light fades with distance.
        # The three values represent the three attenuation constants (constant, linear and quadratic)
        # in the internal lighting equation. The higher the numbers the shorter the light goes.
        self.light.setAttenuation(p3dc.LVector3(0.3, 0.0, 0.0))
        # The cone of a spotlight is controlled by it's lens. This creates the lens
        self.light.setLens(p3dc.PerspectiveLens())
        # This sets the Field of View (fov) of the lens, in degrees for width
        # and height.  The lower the numbers, the tighter the spotlight.
        self.light.getLens().setFov(40, 40)
        #self.light.getLens().setFov(40)
        self.light.getLens().setNearFar(0.5, 50)
        self.light.setColor((0.6, 0.6, 0.8, 1))
        ############################################################
        ####\/########\/########\/########\/########\/########\/####
        #self.light_node.setPosHpr(0, -10, 15, 0, -50, 0) #This does not light the tiles... (similar to https://discourse.panda3d.org/t/shadows-with-directional-light-source-strange-behaviour/10025 )
        self.light_node.setPosHpr(0, 10, 15, 180, -50, 0) #This works as intended
        #self.light_node.setPosHpr(0, 0, 8, 0, -80, 0) #This lights half the tiles but I don't know why this works to a degree but the first one doesn't at all
        ####/\########/\########/\########/\########/\########/\####
        ############################################################
        render().setLight(self.light_node)
        #
        #
        #
        #self.light2 = p3dc.Spotlight("Spot")
        #self.light2_node = render().attachNewNode(self.light2) # generates instance of p3dc.NodePath
        #print("self.light_node",type(self.light2_node))
        #self.light2.setScene(render())
        #self.light2.setShadowCaster(True, 1024, 1024)#.setShadowCaster(True)
        ##self.light.showFrustum()
        ## This exponent value sets how soft the edge of the spotlight is.
        ## 0 means a hard edge. 128 means a very soft edge.
        #self.light2.setExponent(60.0)
        ## Attenuation controls how the light fades with distance.
        ## The three values represent the three attenuation constants (constant, linear and quadratic)
        ## in the internal lighting equation. The higher the numbers the shorter the light goes.
        #self.light2.setAttenuation(p3dc.LVector3(0.3, 0.0, 0.0))
        ## The cone of a spotlight is controlled by it's lens. This creates the lens
        #self.light2.setLens(p3dc.PerspectiveLens())
        ## This sets the Field of View (fov) of the lens, in degrees for width
        ## and height.  The lower the numbers, the tighter the spotlight.
        #self.light2.getLens().setFov(40, 40)
        ##self.light2.getLens().setFov(40)
        #self.light2.getLens().setNearFar(0.5, 50)
        #self.light2.setColor((0.6, 0.6, 0.8, 1))
        #self.light2_node.setPosHpr(0, -10, 15, 0, -50, 0)
        #render().setLight(self.light2_node)

        #self.alight = render().attachNewNode(p3dc.AmbientLight("Ambient"))
        #self.alight.node().setColor(p3dc.LVector4(0.1, 0.1, 0.1, 1))
        #render().setLight(self.alight)

        # Important! Enable the shader generator.
        render().setShaderAuto()

class EngineClass(ape.APE):
    def start(self):
        self.base.start()
        self.scene = ChessScene()
        self.scene.start()

class AppClass(ape.APEApp):
    pass

class MainWindowClass(ape.APEWindow):
    pass

class PandaWidget(ape.PandaWidget):
    pass

class BaseClass(ape.APEPandaBase):
    def start(self):
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

#region piece classes
class Piece(object):
    """
    Class for a piece. \n
    This just handles loading the model and setting initial position and colour
    """
    model = "chessboard_models/pawn" # Placeholder overwritten by subclasses
    def __init__(self, square, colour):
        self.obj = loader().loadModel(self.model)
        self.obj.reparentTo(render())
        self.obj.setColor(colour)
        self.obj.setPos(SquarePos(square))


# Classes for each type of chess piece
# Obviously, we could have done this by just passing a string to Piece's init.
# But if you wanted to make rules for how the pieces move, a good place to start
# would be to make an isValidMove(toSquare) method for each piece type
# and then check if the destination square is acceptable during ReleasePiece
class Pawn(Piece):
    model = "chessboard_models/pawn"

class King(Piece):
    model = "chessboard_models/king"

class Queen(Piece):
    model = "chessboard_models/queen"

class Bishop(Piece):
    model = "chessboard_models/bishop"

class Knight(Piece):
    model = "chessboard_models/knight"

class Rook(Piece):
    model = "chessboard_models/rook"
        
#endregion piece classes
    
if __name__ == '__main__':
    ape.start(WindowTitle,EngineClass,BaseClass,AppClass,MainWindowClass,PandaWidget,True)



