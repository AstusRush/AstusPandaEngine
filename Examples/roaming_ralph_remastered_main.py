"""

Roaming Ralph Sample Remastered

WIP

"""

# The Pipeline Can be toggled on/off with this
SupportsRenderPipeline = True

import datetime
import platform
WindowTitle = "APE Roaming-Ralph Remastered"
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
import math
import sys
sys.path.append('..')

# Panda imports
import panda3d as p3d
import panda3d.core as p3dc
from direct.showbase.ShowBase import ShowBase
from direct.gui.OnscreenText import OnscreenText
from direct.actor.Actor import Actor

# AGE and APE imports
from AGeLib import *

import AstusPandaEngine as ape # pylint: disable=import-error
from AstusPandaEngine import window, engine # pylint: disable=import-error



# Function to put instructions on the screen.
def addInstructions(pos, msg):
    return OnscreenText(text=msg, style=1, fg=(1, 1, 1, 1),
                        pos=(-0.9, pos - 0.2), align=p3dc.TextNode.ALeft, scale=.035)
sys.path.append('..')


class scene(ape.APEScene):
    def start(self):
        ape.base().start()

class EngineClass(ape.APE):
    def start(self):
        self.Scene = scene()
        self.Scene.start()

class AppClass(ape.APEApp):
    pass

class MainWindowClass(ape.APEWindow):
    pass

class PandaWidget(ape.PandaWidget):
    pass

class RoamingRalphDemo(ape.APEPandaBase):
    def start(self):

        if self.render_pipeline:
            # Set time of day
            self.render_pipeline.daytime_mgr.time = "7:40"

            # Use a special effect for rendering the scene, this is because the
            # roaming ralph model has no normals or valid materials
            self.render_pipeline.set_effect(ape.render(), "_pipeline_effect-texture.yaml", {}, sort=250)

        self.keyMap = {"left":0, "right":0, "forward":0, "backward":0, "cam-left":0, "cam-right":0}
        self.speed = 1.0
        ape.base().win.setClearColor(p3dc.Vec4(0,0,0,1))
        
        self.collisionVisible = False
        
        # Post the instructions
        
        self.inst4 = addInstructions(0.90, "[W]  Run Ralph Forward")
        self.inst4 = addInstructions(0.85, "[S]  Run Ralph Backward")
        self.inst2 = addInstructions(0.80, "[A]  Rotate Ralph Left")
        self.inst3 = addInstructions(0.75, "[D]  Rotate Ralph Right")
        self.inst6 = addInstructions(0.70, "[Left Arrow]  Rotate Camera Left")
        self.inst7 = addInstructions(0.65, "[Right Arrow]  Rotate Camera Right")
        self.inst7 = addInstructions(0.95, "[C]  Toggle Collision Visibility")
        
        # Set up the environment
        #
        # This environment model contains collision meshes.  If you look
        # in the egg file, you will see the following:
        #
        #    <Collide> { Polyset keep descend }
        #
        # This tag causes the following mesh to be converted to a collision
        # mesh -- a mesh which is optimized for collision, not rendering.
        # It also keeps the original mesh, so there are now two copies ---
        # one optimized for rendering, one for collisions.
        
        #self.environ = ape.loader().loadModel("roaming_ralph_pipeline_resources/world")
        self.environ = ape.loader().loadModel("roaming_ralph_models/world")
        self.environ.reparentTo(ape.render())
        self.environ.setPos(0,0,0)
        
        
        # Remove wall nodes
        self.environ.find("**/wall").remove_node()

        # Create the main character, Ralph
        self.ralph = Actor("roaming_ralph_pipeline_resources/ralph",
                                 {"run":"roaming_ralph_pipeline_resources/ralph-run",
                                  "walk":"roaming_ralph_pipeline_resources/ralph-walk",
                                  "stand":"roaming_ralph_pipeline_resources/ralph"})
        self.ralph.reparentTo(ape.render())
        self.ralph.setScale(.2)
        self.ralph.setPos(p3dc.Vec3(-110.9, 29.4, 1.8))

        # Create a floater object.  We use the "floater" as a temporary
        # variable in a variety of calculations.

        self.floater = p3dc.NodePath(p3dc.PandaNode("floater"))
        self.floater.reparentTo(ape.render())

        # Accept the control keys for movement and rotation
        
        self.accept("a", self.setKey, ["left",1])
        self.accept("d", self.setKey, ["right",1])
        self.accept("w", self.setKey, ["forward",1])
        self.accept("s", self.setKey, ["backward",1])
        self.accept("arrow_left", self.setKey, ["cam-left",1])
        self.accept("arrow_right", self.setKey, ["cam-right",1])
        self.accept("a-up", self.setKey, ["left",0])
        self.accept("d-up", self.setKey, ["right",0])
        self.accept("w-up", self.setKey, ["forward",0])
        self.accept("s-up", self.setKey, ["backward",0])
        self.accept("arrow_left-up", self.setKey, ["cam-left",0])
        self.accept("arrow_right-up", self.setKey, ["cam-right",0])
        self.accept("=", self.adjustSpeed, [0.25])
        self.accept("+", self.adjustSpeed, [0.25])
        self.accept("-", self.adjustSpeed, [-0.25])
        self.accept("c", self.toggleCollisionVisibility)
        self.accept("3",self.resetPos)

        ape.base().taskMgr.add(self.move,"moveTask")

        # Game state variables
        self.isMoving = False

        # Set up the camera

        ape.base().disableMouse()
        ape.base().camera.setPos(self.ralph.getX() + 10,self.ralph.getY() + 10, 2)
        ape.base().camLens.setFov(80)

        # We will detect the height of the terrain by creating a collision
        # ray and casting it downward toward the terrain.  One ray will
        # start above ralph's head, and the other will start above the camera.
        # A ray may hit the terrain, or it may hit a rock or a tree.  If it
        # hits the terrain, we can detect the height.  If it hits anything
        # else, we rule that the move is illegal.
        self.cTrav = p3dc.CollisionTraverser()

        self.ralphGroundRay = p3dc.CollisionRay()
        self.ralphGroundRay.setOrigin(0,0,1000)
        self.ralphGroundRay.setDirection(0,0,-1)
        self.ralphGroundCol = p3dc.CollisionNode('ralphRay')
        self.ralphGroundCol.addSolid(self.ralphGroundRay)
        self.ralphGroundCol.setFromCollideMask(p3dc.CollideMask.bit(0))
        self.ralphGroundCol.setIntoCollideMask(p3dc.CollideMask.allOff())
        self.ralphGroundColNp = self.ralph.attachNewNode(self.ralphGroundCol)
        self.ralphGroundHandler = p3dc.CollisionHandlerQueue()
        self.cTrav.addCollider(self.ralphGroundColNp, self.ralphGroundHandler)

        self.camGroundRay = p3dc.CollisionRay()
        self.camGroundRay.setOrigin(0,0,1000)
        self.camGroundRay.setDirection(0,0,-1)
        self.camGroundCol = p3dc.CollisionNode('camRay')
        self.camGroundCol.addSolid(self.camGroundRay)
        self.camGroundCol.setFromCollideMask(p3dc.CollideMask.bit(0))
        self.camGroundCol.setIntoCollideMask(p3dc.CollideMask.allOff())
        self.camGroundColNp = ape.base().camera.attachNewNode(self.camGroundCol)
        self.camGroundHandler = p3dc.CollisionHandlerQueue()
        self.cTrav.addCollider(self.camGroundColNp, self.camGroundHandler)

        # Create some lighting
        ambientLight = p3dc.AmbientLight("ambientLight")
        ambientLight.setColor(p3dc.Vec4(.3, .3, .3, 1))
        directionalLight = p3dc.DirectionalLight("directionalLight")
        directionalLight.setDirection(p3dc.Vec3(-5, -5, -5))
        directionalLight.setColor(p3dc.Vec4(1, 1, 1, 1))
        directionalLight.setSpecularColor(p3dc.Vec4(1, 1, 1, 1))
        ape.render().setLight(ape.render().attachNewNode(ambientLight))
        ape.render().setLight(ape.render().attachNewNode(directionalLight))

    #Records the state of the arrow keys
    def setKey(self, key, value):
        self.keyMap[key] = value

    # Adjust movement speed
    def adjustSpeed(self, delta):
        newSpeed = self.speed + delta
        if 0 <= newSpeed <= 3:
          self.speed = newSpeed

    def toggleCollisionVisibility(self):
        if not self.collisionVisible:
            self.collisionVisible = True
            # Show the collision rays
            self.ralphGroundColNp.show()
            self.camGroundColNp.show()

            # Show a visual representation of the collisions occurring
            self.cTrav.showCollisions(ape.render())
        else:
            self.collisionVisible = False
            # Hide the collision rays
            self.ralphGroundColNp.hide()
            self.camGroundColNp.hide()

            # Hide the visual representation of the collisions occurring
            self.cTrav.hideCollisions()

    def resetPos(self):
        self.ralph.setPos(p3dc.Vec3(-110.9, 29.4, 1.8))

        # Keep the camera at one foot above the terrain,
        # or two feet above ralph, whichever is greater.

        entries = []
        for i in range(self.camGroundHandler.getNumEntries()):
            entry = self.camGroundHandler.getEntry(i)
            entries.append(entry)
        if (len(entries)>0) and (entries[0].getIntoNode().getName() == "terrain"):
            ape.base().camera.setZ(entries[0].getSurfacePoint(ape.render()).getZ()+1.0)
        if (ape.base().camera.getZ() < self.ralph.getZ() + 2.0):
            ape.base().camera.setZ(self.ralph.getZ() + 2.0)

        # The camera should look in ralph's direction,
        # but it should also try to stay horizontal, so look at
        # a floater which hovers above ralph's head.

        self.floater.setPos(self.ralph.getPos())
        self.floater.setZ(self.ralph.getZ() + 2.0)
        ape.base().camera.lookAt(self.floater)

    # Accepts arrow keys to move either the player or the menu cursor,
    # Also deals with grid checking and collision detection
    def move(self, task):

        # If the camera-left key is pressed, move camera left.
        # If the camera-right key is pressed, move camera right.
        
        ape.base().camera.lookAt(self.ralph)
        if (self.keyMap["cam-left"]!=0):
            ape.base().camera.setX(ape.base().camera, +20 * p3dc.ClockObject.getGlobalClock().getDt())
        if (self.keyMap["cam-right"]!=0):
            ape.base().camera.setX(ape.base().camera, -20 * p3dc.ClockObject.getGlobalClock().getDt())

        # save ralph's initial position so that we can restore it,
        # in case he falls off the map or runs into something.

        startpos = self.ralph.getPos()

        # If a move-key is pressed, move ralph in the specified direction.

        if (self.keyMap["left"]!=0):
            self.ralph.setH(self.ralph.getH() + 300 * p3dc.ClockObject.getGlobalClock().getDt())
        elif (self.keyMap["right"]!=0):
            self.ralph.setH(self.ralph.getH() - 300 * p3dc.ClockObject.getGlobalClock().getDt())
        if (self.keyMap["forward"]!=0):
            self.ralph.setY(self.ralph, -25 * self.speed * p3dc.ClockObject.getGlobalClock().getDt())
        elif (self.keyMap["backward"]!=0):
            self.ralph.setY(self.ralph, 25 * self.speed * p3dc.ClockObject.getGlobalClock().getDt())

        # If ralph is moving, loop the run animation.
        # If he is standing still, stop the animation.

        #if (self.keyMap["forward"]!=0) or (self.keyMap["backward"]!=0) or \
        #   (self.keyMap["left"]!=0) or (self.keyMap["right"]!=0):
        if self.keyMap["forward"] or self.keyMap["backward"] or self.keyMap["left"] or self.keyMap["right"]:
            if self.isMoving is False:
                self.ralph.loop("run")
                self.isMoving = True
        else:
            if self.isMoving:
                self.ralph.stop()
                self.ralph.pose("walk",6)
                self.isMoving = False

        # If the camera is too far from ralph, move it closer.
        # If the camera is too close to ralph, move it farther.

        camvec = self.ralph.getPos() - ape.base().camera.getPos()
        camvec.setZ(0)
        camdist = camvec.length()
        camvec.normalize()
        if (camdist > 10.0):
            ape.base().camera.setPos(ape.base().camera.getPos() + camvec*(camdist-10))
            camdist = 10.0
        if (camdist < 5.0):
            ape.base().camera.setPos(ape.base().camera.getPos() - camvec*(5-camdist))
            camdist = 5.0

        
        # Normally, we would have to call traverse() to check for collisions.
        # However, the class ShowBase that we inherit from has a task to do
        # this for us, if we assign a p3dc.CollisionTraverser to self.cTrav.
        # 
        # NOTE: This line must be here to avoid getting stuck:
        # Without the following line Ralph often gets stuck INSIDE objects without a way to escape.
        # With this line ralph can run through most trees but still collides with rocks.
        #   But more importantly ralph no longer gets stuck inside objects and a little phasing if to be preferred over getting stuck.
        self.cTrav.traverse(ape.render())

        # Adjust ralph's Z coordinate.  If ralph's ray hit terrain,
        # update his Z. If it hit anything else, or didn't hit anything, put
        # him back where he was last frame.

        #entries = []
        #for i in range(self.ralphGroundHandler.getNumEntries()):
        #    entry = self.ralphGroundHandler.getEntry(i)
        #    entries.append(entry)
            
        entries = list(self.ralphGroundHandler.getEntries())
        entries.sort(key=lambda x: x.getSurfacePoint(self.render).getZ())

        if len(entries) > 0 and entries[0].getIntoNode().getName() == "terrain":
            self.ralph.setZ(entries[0].getSurfacePoint(ape.render()).getZ())
        else:
            self.ralph.setPos(startpos)

        # Keep the camera at one foot above the terrain,
        # or two feet above ralph, whichever is greater.

        entries = []
        for i in range(self.camGroundHandler.getNumEntries()):
            entry = self.camGroundHandler.getEntry(i)
            entries.append(entry)
        if (len(entries)>0) and (entries[0].getIntoNode().getName() == "terrain"):
            ape.base().camera.setZ(entries[0].getSurfacePoint(ape.render()).getZ()+1.0)
        if (ape.base().camera.getZ() < self.ralph.getZ() + 2.0):
            ape.base().camera.setZ(self.ralph.getZ() + 2.0)

        # The camera should look in ralph's direction,
        # but it should also try to stay horizontal, so look at
        # a floater which hovers above ralph's head.

        self.floater.setPos(self.ralph.getPos())
        self.floater.setZ(self.ralph.getZ() + 2.0)
        ape.base().camera.lookAt(self.floater)

        return task.cont




if __name__ == '__main__':
    ape.start(WindowTitle,EngineClass,RoamingRalphDemo,AppClass,MainWindowClass,PandaWidget,True,SupportsRenderPipeline)
