SupportsRenderPipeline = False

import datetime
import platform
WindowTitle = "APE-Procedural-Terrain-1-Interactive-Example"
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

import AstusPandaEngine as ape # pylint: disable = import-error
from AstusPandaEngine import window, engine, base, render, loader # pylint: disable = import-error

import ProcTer_1_static_Function

sys.path.append('..')

############################################

#region Original Classes

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

class Terrain(ape.APEPandaBase):
    def start(self):
        self.seedGen = np.random.default_rng()
        self.rng = np.random.default_rng()
        #if self.render_pipeline:
        #    # Set time of day
        #    self.render_pipeline.daytime_mgr.time = "7:40"
        #    
        #    # Use a special effect for rendering the scene.
        #    # This is necessary because there are no normals or valid materials.
        #    self.render_pipeline.set_effect(ape.render(), "_pipeline_effect-vertex-colour.yaml", {}, sort=250)
            
        # Set up camera #TODO: Improve camera behaviour by creating own 
        base().setFrameRateMeter(True)
        #base().disableMouse()
        
        base().trackball.node().set_pos(-12,0,-12)
        
        #Following does not work
        #base().trackball.set_pos(-120,0,-12)
        #base().trackball.setP(5)
        #base().trackball.look_at(self.cols/2,300,0)
        
        #base().enableMouse()
        
        # Temporary Call
        self.makeTerrain_temp()

    def gen(self, rows = 600, cols = 300, seed = 0):
        seed = int(seed)
        if not seed:
            seed = self.seedGen.integers(1000000)
        rng = np.random.default_rng(seed)
        #TODO: ...

    def makeTerrain(self,matrix):
        # TODO: Generate Terrain
        pass

    def makeTerrain_temp(self, rows = 600, cols = 300, seed = 0):
        seed = int(seed)
        if not seed:
            seed = self.seedGen.integers(1000000)
        rng = np.random.default_rng(seed)
        
        #region Create point lights #TODO: Rework and improve
        #IMPROVE: self.plights should be used from the beginning
        plights = []
        
        for i in range(0,int(cols/5),2):
            plight = p3dc.PointLight("plight")
            plight.setColor(p3dc.VBase4(1, 1, 1, 1))
            #IMPROVE: The next line is superfluous and the line after that should use append
            plights.append(plight)
            plights[i] = self.render.attachNewNode(plight)
            x,y,_ = self.camera.get_pos()
            plights[i].setPos(cols/2+((i-int(i/2))*10),y+20,5)
            self.render.set_light(plights[i])
            
            #CLEANUP: reduce code duplication
            plight = p3dc.PointLight("plight")
            plight.setColor(p3dc.VBase4(1, 1, 1, 1))
            #IMPROVE: The next line is superfluous and the line after that should use append
            plights.append(plight)
            plights[i+1] = self.render.attachNewNode(plight)
            x,y,_ = self.camera.get_pos()
            plights[i+1].setPos(cols/2+((i-int(i/2))*10),y+20,10)
            self.render.set_light(plights[i+1])
        
        self.plights = plights #CLEANUP: replace plights with self.plights
        #endregion Create point lights
        #region #TODO: What is done here?
        Format = p3dc.GeomVertexFormat.getV3c4()
        self.vdata = p3dc.GeomVertexData('name', Format, p3dc.Geom.UHStatic)
        self.vdata.setNumRows(cols*rows)
        self.vertex = p3dc.GeomVertexWriter(self.vdata, 'vertex')
        self.color = p3dc.GeomVertexWriter(self.vdata, 'color')
        
        pz = [rng.uniform(-1,1)]
        for i in range(rows):
            pz.append(rng.uniform(pz[i-1]-1,pz[i]+1))
        for y in range(0,rows):
            for x in range(0,cols):
                nz1 = rng.uniform(pz[x]   - 1, pz[x]   + 1)
                nz2 = rng.uniform(pz[x-1] - 1, pz[x-1] + 1)
                nz3 = rng.uniform(pz[x+1] - 1, pz[x+1] + 1)
                nz = (nz1 + nz2 + nz3) / 3
                self.vertex.add_data3f((x, y+1, nz   ))
                self.vertex.add_data3f((x, y  , pz[x]))
                if nz < -5:
                    self.color.add_data4f(0.2,0.1,0,1)
                elif nz < -3:
                    self.color.add_data4f(0,0.2,0.1,1)
                elif nz < 0:
                    self.color.add_data4f(0,0.4,0.2,1)
                elif nz < 2:
                    self.color.add_data4f(0.4,0.4,0.4,1)
                else:
                    self.color.add_data4f(1,1,1,1)
                if nz < -5:
                    self.color.add_data4f(0.2,0.1,0,1)
                elif nz < -3:
                    self.color.add_data4f(0,0.2,0.1,1)
                elif pz[x] < 0:
                    self.color.add_data4f(0,0.4,0.2,1)
                elif pz[x] < 2:
                    self.color.add_data4f(0.4,0.4,0.4,1)
                else:
                    self.color.add_data4f(1,1,1,1)
                pz[x] = nz

        geom = p3dc.Geom(self.vdata)
        for y in range(0, rows):
            prim = p3dc.GeomTristrips(p3dc.Geom.UH_static)
            prim.addVertex(y*cols*2)
            prim.add_next_vertices((cols*2)-1)
            prim.close_primitive()
            geom.addPrimitive(prim)

        nodeTris = p3dc.GeomNode("TriStrips")
        nodeTris.addGeom(geom)
        try:
            self.nodeTrisPath.removeNode()
            del self.nodeTrisPath
        except AttributeError:
            NC(4,"could not delete nodeTrisPath",exc=True)
        except:
            NC(3,"could not delete nodeTrisPath",exc=True)
        self.nodeTrisPath = self.render.attachNewNode(nodeTris)
        
        #endregion What is done here?

    def old(self):
        #region Create point lights #TODO: Rework and improve
        #IMPROVE: self.plights should be used from the beginning
        plights = []

        for i in range(0,int(self.cols/5),2):
            plight = p3dc.PointLight("plight")
            plight.setColor(p3dc.VBase4(1, 1, 1, 1))
            #IMPROVE: The next line is superfluous and the line after that should use append
            plights.append(plight)
            plights[i] = self.render.attachNewNode(plight)
            x,y,_ = self.camera.get_pos()
            plights[i].setPos(self.cols/2+((i-int(i/2))*10),y+20,5)
            self.render.set_light(plights[i])
            
            #CLEANUP: reduce code duplication
            plight = p3dc.PointLight("plight")
            plight.setColor(p3dc.VBase4(1, 1, 1, 1))
            #IMPROVE: The next line is superfluous and the line after that should use append
            plights.append(plight)
            plights[i+1] = self.render.attachNewNode(plight)
            x,y,_ = self.camera.get_pos()
            plights[i+1].setPos(self.cols/2+((i-int(i/2))*10),y+20,10)
            self.render.set_light(plights[i+1])

        self.plights = plights #CLEANUP: replace plights with self.plights
        #endregion Create point lights
        ###
        ###
        #region #TODO: What is done here?
        Format = p3dc.GeomVertexFormat.getV3c4()
        vdata = p3dc.GeomVertexData('name', Format, p3dc.Geom.UHStatic)
        vdata.setNumRows(self.cols*self.rows)
        self.vertex = p3dc.GeomVertexWriter(vdata, 'vertex')
        self.color = p3dc.GeomVertexWriter(vdata, 'color')

        pz = [random.uniform(-1,1)]
        for i in range(self.rows):
            pz.append(random.uniform(pz[i-1]-1,pz[i]+1))
        for y in range(0,self.rows):
            for x in range(0,self.cols):
                nz1 = random.uniform(pz[x]   - 1, pz[x]   + 1)
                nz2 = random.uniform(pz[x-1] - 1, pz[x-1] + 1)
                nz3 = random.uniform(pz[x+1] - 1, pz[x+1] + 1)
                nz = (nz1 + nz2 + nz3) / 3
                self.vertex.add_data3f((x, y+1, nz   ))
                self.vertex.add_data3f((x, y  , pz[x]))
                if nz < -5:
                    self.color.add_data4f(0.2,0.1,0,1)
                elif nz < -3:
                    self.color.add_data4f(0,0.2,0.1,1)
                elif nz < 0:
                    self.color.add_data4f(0,0.4,0.2,1)
                elif nz < 2:
                    self.color.add_data4f(0.4,0.4,0.4,1)
                else:
                    self.color.add_data4f(1,1,1,1)
                if nz < -5:
                    self.color.add_data4f(0.2,0.1,0,1)
                elif nz < -3:
                    self.color.add_data4f(0,0.2,0.1,1)
                elif pz[x] < 0:
                    self.color.add_data4f(0,0.4,0.2,1)
                elif pz[x] < 2:
                    self.color.add_data4f(0.4,0.4,0.4,1)
                else:
                    self.color.add_data4f(1,1,1,1)
                pz[x] = nz
                #print(nz)
        self.pz = pz

        geom = p3dc.Geom(vdata)
        for y in range(0, self.rows):
            prim = p3dc.GeomTristrips(p3dc.Geom.UH_static)
            prim.addVertex(y*self.cols*2)
            prim.add_next_vertices((self.cols*2)-1)
            prim.close_primitive()
            geom.addPrimitive(prim)

        nodeTris = p3dc.GeomNode("TriStrips")
        nodeTris.addGeom(geom)
        self.nodeTrisPath = self.render.attachNewNode(nodeTris)
        #self.task_mgr.add(self.moveForwardTask,"moveForwardTask")

        self.vdata = vdata #CLEANUP: replace vdata with self.vdata
        self.newNodePath = [] #CLEANUP: Remove
        self.counter = 0 #CLEANUP: Remove
        self.rows1 = self.rows #CLEANUP: Remove
        #endregion What is done here?

    def get_code(self):
        return inspect.getsource(self.makeTerrain_temp)

    def apply_code(self,code):
        try:
            exec(code)
        except:
            NC(exc=sys.exc_info(),func="Terrain.apply_code",input=code)

    def g(self, rows = 300, cols = 600, seed = 0):
        importlib.reload(ProcTer_1_static_Function)
        t = datetime.datetime.now()
        s = ProcTer_1_static_Function.gen(self, rows = rows, cols = cols, seed = seed)
        t = datetime.datetime.now() - t
        NC(10,"{} : Done with seed {} . It took {}".format(datetime.datetime.now().strftime('%H:%M:%S'),s,t))

        
    #region Perlin Noise ### From https://github.com/pvigier/perlin-numpy under MIT License:
    def interpolant(self, t):
        return t*t*t*(t*(t*6 - 15) + 10)


    def generate_perlin_noise_2d(self, shape, res, tileable=(False, False), interpolant=None):
        """Generate a 2D numpy array of perlin noise.
        Args:
            shape: The shape of the generated array (tuple of two ints).
                This must be a multple of res.
            res: The number of periods of noise to generate along each
                axis (tuple of two ints). Note shape must be a multiple of
                res.
            tileable: If the noise should be tileable along each axis
                (tuple of two bools). Defaults to (False, False).
            interpolant: The interpolation function, defaults to
                t*t*t*(t*(t*6 - 15) + 10).
        Returns:
            A numpy array of shape shape with the generated noise.
        Raises:
            ValueError: If shape is not a multiple of res.
        """
        if interpolant == None:
            interpolant = self.interpolant
        delta = (res[0] / shape[0], res[1] / shape[1])
        d = (shape[0] // res[0], shape[1] // res[1])
        grid = np.mgrid[0:res[0]:delta[0], 0:res[1]:delta[1]].transpose(1, 2, 0) % 1
        # Gradients
        #angles = 2*np.pi*np.random.rand(res[0]+1, res[1]+1)
        angles = 2*np.pi*self.rng.random((res[0]+1, res[1]+1))
        gradients = np.dstack((np.cos(angles), np.sin(angles)))
        if tileable[0]:
            gradients[-1,:] = gradients[0,:]
        if tileable[1]:
            gradients[:,-1] = gradients[:,0]
        gradients = gradients.repeat(d[0], 0).repeat(d[1], 1)
        g00 = gradients[    :-d[0],    :-d[1]]
        g10 = gradients[d[0]:     ,    :-d[1]]
        g01 = gradients[    :-d[0],d[1]:     ]
        g11 = gradients[d[0]:     ,d[1]:     ]
        # Ramps
        n00 = np.sum(np.dstack((grid[:,:,0]  , grid[:,:,1]  )) * g00, 2)
        n10 = np.sum(np.dstack((grid[:,:,0]-1, grid[:,:,1]  )) * g10, 2)
        n01 = np.sum(np.dstack((grid[:,:,0]  , grid[:,:,1]-1)) * g01, 2)
        n11 = np.sum(np.dstack((grid[:,:,0]-1, grid[:,:,1]-1)) * g11, 2)
        # Interpolation
        t = interpolant(grid)
        n0 = n00*(1-t[:,:,0]) + t[:,:,0]*n10
        n1 = n01*(1-t[:,:,0]) + t[:,:,0]*n11
        return np.sqrt(2)*((1-t[:,:,1])*n0 + t[:,:,1]*n1)


    def generate_fractal_noise_2d( self,
            shape, res, octaves=1, persistence=0.5,
            lacunarity=2, tileable=(False, False),
            interpolant=interpolant
            ):
        """Generate a 2D numpy array of fractal noise.
        Args:
            shape: The shape of the generated array (tuple of two ints).
                This must be a multiple of lacunarity**(octaves-1)*res.
            res: The number of periods of noise to generate along each
                axis (tuple of two ints). Note shape must be a multiple of
                (lacunarity**(octaves-1)*res).
            octaves: The number of octaves in the noise. Defaults to 1.
            persistence: The scaling factor between two octaves.
            lacunarity: The frequency factor between two octaves.
            tileable: If the noise should be tileable along each axis
                (tuple of two bools). Defaults to (False, False).
            interpolant: The, interpolation function, defaults to
                t*t*t*(t*(t*6 - 15) + 10).
        Returns:
            A numpy array of fractal noise and of shape shape generated by
            combining several octaves of perlin noise.
        Raises:
            ValueError: If shape is not a multiple of
                (lacunarity**(octaves-1)*res).
        """
        noise = np.zeros(shape)
        frequency = 1
        amplitude = 1
        for _ in range(octaves):
            noise += amplitude * self.generate_perlin_noise_2d(
                shape, (frequency*res[0], frequency*res[1]), tileable, self.interpolant
            )
            frequency *= lacunarity
            amplitude *= persistence
        return noise
    #endregion Perlin Noise

#endregion Original Classes

#region Interactive Terrain

class InteractiveTerrain(ape.APEPandaBase):
    # DISCLAIMER:
    # This example works by detecting collision with the terrain.
    # This is a bad way of doing this and is only here as an example
    # The correct way would be to use the matrix that describes the terrain to adjust Ralf's height.
    # See https://discourse.panda3d.org/t/adding-collision-to-a-generated-terrain/5867
    def start(self):
        self.seedGen = np.random.default_rng()
        self.rng = np.random.default_rng()
        ######################################

        if self.render_pipeline:
            # Set time of day
            self.render_pipeline.daytime_mgr.time = "5:20"

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
        self.inst6 = addInstructions(0.70, "[Q] OR [Left Arrow]  Rotate Camera Left")
        self.inst7 = addInstructions(0.65, "[E] OR [Right Arrow]  Rotate Camera Right")
        self.inst7 = addInstructions(0.95, "[C]  Toggle Collision Visibility")
        
        # Set up the environment
        #
        self.g() # MAYBE: Look into https://docs.panda3d.org/1.10/python/programming/physics/bullet/collision-shapes#heightfield-shape
        self.taskMgr.add(self.updateTask, "update")
        self.terrain.getRoot().setCollideMask(p3dc.CollideMask.bit(0))

        # Create the main character, Ralph
        self.ralph = Actor("roaming_ralph_pipeline_resources/ralph",
                                 {"run":"roaming_ralph_pipeline_resources/ralph-run",
                                  "walk":"roaming_ralph_pipeline_resources/ralph-walk",
                                  "stand":"roaming_ralph_pipeline_resources/ralph"})
        self.ralph.reparentTo(ape.render())
        self.ralph.setScale(.2)
        self.ralph.setPos(p3dc.Vec3(150,150,self.terrainMatrix[150,150]))

        # Create a floater object.  We use the "floater" as a temporary
        # variable in a variety of calculations.

        self.floater = p3dc.NodePath(p3dc.PandaNode("floater"))
        self.floater.reparentTo(ape.render())

        # Accept the control keys for movement and rotation
        
        self.accept("a", self.setKey, ["left",1])
        self.accept("d", self.setKey, ["right",1])
        self.accept("w", self.setKey, ["forward",1])
        self.accept("s", self.setKey, ["backward",1])
        self.accept("q", self.setKey, ["cam-left",1])
        self.accept("e", self.setKey, ["cam-right",1])
        self.accept("arrow_left", self.setKey, ["cam-left",1])
        self.accept("arrow_right", self.setKey, ["cam-right",1])
        self.accept("a-up", self.setKey, ["left",0])
        self.accept("d-up", self.setKey, ["right",0])
        self.accept("w-up", self.setKey, ["forward",0])
        self.accept("s-up", self.setKey, ["backward",0])
        self.accept("q-up", self.setKey, ["cam-left",0])
        self.accept("e-up", self.setKey, ["cam-right",0])
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
        #ambientLight = p3dc.AmbientLight("ambientLight")
        #ambientLight.setColor(p3dc.Vec4(.3, .3, .3, 1))
        #directionalLight = p3dc.DirectionalLight("directionalLight")
        #directionalLight.setDirection(p3dc.Vec3(-5, -5, -5))
        #directionalLight.setColor(p3dc.Vec4(1, 1, 1, 1))
        #directionalLight.setSpecularColor(p3dc.Vec4(1, 1, 1, 1))
        #ape.render().setLight(ape.render().attachNewNode(ambientLight))
        #ape.render().setLight(ape.render().attachNewNode(directionalLight))
        #

    def updateTask(self, task):
        self.terrain.update()
        return task.cont

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
        self.ralph.setPos(p3dc.Vec3(150,150,self.terrainMatrix[150,150]))
        
        # Keep the camera at one foot above the terrain,
        # or two feet above ralph, whichever is greater.

        entries = []
        for i in range(self.camGroundHandler.getNumEntries()):
            entry = self.camGroundHandler.getEntry(i)
            entries.append(entry)
        try:
            if len(entries)>0 and entries[0].getIntoNode().getParents()[0].getName() == "terrain":
                ape.base().camera.setZ(entries[0].getSurfacePoint(ape.render()).getZ()+1.0)
        except: # In case the GeomMipMap part has not been assigned the parent we need to check for names beginning with gmm
            if len(entries)>0 and entries[0].getIntoNode().getName().startswith("gmm"):
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
        try:
            if len(entries) > 0 and entries[0].getIntoNode().getParents()[0].getName() == "terrain":
                self.ralph.setZ(entries[0].getSurfacePoint(ape.render()).getZ())
            else:
                self.ralph.setPos(startpos)
        except: # In case the GeomMipMap part has not been assigned the parent we need to check for names beginning with gmm
            if len(entries) > 0 and entries[0].getIntoNode().getName().startswith("gmm"):
                self.ralph.setZ(entries[0].getSurfacePoint(ape.render()).getZ())
            else:
                self.ralph.setPos(startpos)

        # Keep the camera at one foot above the terrain,
        # or two feet above ralph, whichever is greater.

        entries = []
        for i in range(self.camGroundHandler.getNumEntries()):
            entry = self.camGroundHandler.getEntry(i)
            entries.append(entry)
        try:
            if len(entries)>0 and entries[0].getIntoNode().getParents()[0].getName() == "terrain":
                ape.base().camera.setZ(entries[0].getSurfacePoint(ape.render()).getZ()+1.0)
        except: # In case the GeomMipMap part has not been assigned the parent we need to check for names beginning with gmm
            if len(entries)>0 and entries[0].getIntoNode().getName().startswith("gmm"):
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
        
    def makeTerrain_temp(self, rows = 600, cols = 300, seed = 0):
        seed = int(seed)
        if not seed:
            seed = self.seedGen.integers(1000000)
        rng = np.random.default_rng(seed)
        
        #region Create point lights #TODO: Rework and improve
        #IMPROVE: self.plights should be used from the beginning
        plights = []
        
        for i in range(0,int(cols/5),2):
            plight = p3dc.PointLight("plight")
            plight.setColor(p3dc.VBase4(1, 1, 1, 1))
            #IMPROVE: The next line is superfluous and the line after that should use append
            plights.append(plight)
            plights[i] = self.render.attachNewNode(plight)
            x,y,_ = self.camera.get_pos()
            plights[i].setPos(cols/2+((i-int(i/2))*10),y+20,5)
            self.render.set_light(plights[i])
            
            #CLEANUP: reduce code duplication
            plight = p3dc.PointLight("plight")
            plight.setColor(p3dc.VBase4(1, 1, 1, 1))
            #IMPROVE: The next line is superfluous and the line after that should use append
            plights.append(plight)
            plights[i+1] = self.render.attachNewNode(plight)
            x,y,_ = self.camera.get_pos()
            plights[i+1].setPos(cols/2+((i-int(i/2))*10),y+20,10)
            self.render.set_light(plights[i+1])
        
        self.plights = plights #CLEANUP: replace plights with self.plights
        #endregion Create point lights
        #region #TODO: What is done here?
        Format = p3dc.GeomVertexFormat.getV3c4()
        self.vdata = p3dc.GeomVertexData('name', Format, p3dc.Geom.UHStatic)
        self.vdata.setNumRows(cols*rows)
        self.vertex = p3dc.GeomVertexWriter(self.vdata, 'vertex')
        self.color = p3dc.GeomVertexWriter(self.vdata, 'color')
        
        pz = [rng.uniform(-1,1)]
        for i in range(rows):
            pz.append(rng.uniform(pz[i-1]-1,pz[i]+1))
        for y in range(0,rows):
            for x in range(0,cols):
                nz1 = rng.uniform(pz[x]   - 1, pz[x]   + 1)
                nz2 = rng.uniform(pz[x-1] - 1, pz[x-1] + 1)
                nz3 = rng.uniform(pz[x+1] - 1, pz[x+1] + 1)
                nz = (nz1 + nz2 + nz3) / 3
                self.vertex.add_data3f((x, y+1, nz   ))
                self.vertex.add_data3f((x, y  , pz[x]))
                if nz < -5:
                    self.color.add_data4f(0.2,0.1,0,1)
                elif nz < -3:
                    self.color.add_data4f(0,0.2,0.1,1)
                elif nz < 0:
                    self.color.add_data4f(0,0.4,0.2,1)
                elif nz < 2:
                    self.color.add_data4f(0.4,0.4,0.4,1)
                else:
                    self.color.add_data4f(1,1,1,1)
                if nz < -5:
                    self.color.add_data4f(0.2,0.1,0,1)
                elif nz < -3:
                    self.color.add_data4f(0,0.2,0.1,1)
                elif pz[x] < 0:
                    self.color.add_data4f(0,0.4,0.2,1)
                elif pz[x] < 2:
                    self.color.add_data4f(0.4,0.4,0.4,1)
                else:
                    self.color.add_data4f(1,1,1,1)
                pz[x] = nz

        geom = p3dc.Geom(self.vdata)
        for y in range(0, rows):
            prim = p3dc.GeomTristrips(p3dc.Geom.UH_static)
            prim.addVertex(y*cols*2)
            prim.add_next_vertices((cols*2)-1)
            prim.close_primitive()
            geom.addPrimitive(prim)

        nodeTris = p3dc.GeomNode("TriStrips")
        nodeTris.addGeom(geom)
        try:
            self.nodeTrisPath.removeNode()
            del self.nodeTrisPath
        except AttributeError:
            NC(4,"could not delete nodeTrisPath",exc=True)
        except:
            NC(3,"could not delete nodeTrisPath",exc=True)
        self.nodeTrisPath = self.render.attachNewNode(nodeTris)
        
        #endregion What is done here?


    def get_code(self):
        return inspect.getsource(self.makeTerrain_temp)

    def apply_code(self,code):
        try:
            exec(code)
        except:
            NC(exc=sys.exc_info(),func="Terrain.apply_code",input=code)

    def g(self, rows = 300, cols = 600, seed = 0):
        importlib.reload(ProcTer_1_static_Function)
        t = datetime.datetime.now()
        s = ProcTer_1_static_Function.gen(self, rows = rows, cols = cols, seed = seed)
        t = datetime.datetime.now() - t
        NC(10,"{} : Done with seed {} . It took {}".format(datetime.datetime.now().strftime('%H:%M:%S'),s,t))

    def reload(self, rows = 300, cols = 600, seed = 0):
        self.g(rows = rows, cols = cols, seed = seed)
        self.taskMgr.add(self.updateTask, "update")
        self.terrain.getRoot().setCollideMask(p3dc.CollideMask.bit(0))
        self.resetPos()

        
    #region Perlin Noise ### From https://github.com/pvigier/perlin-numpy under MIT License:
    def interpolant(self, t):
        return t*t*t*(t*(t*6 - 15) + 10)


    def generate_perlin_noise_2d(self, shape, res, tileable=(False, False), interpolant=None):
        """Generate a 2D numpy array of perlin noise.
        Args:
            shape: The shape of the generated array (tuple of two ints).
                This must be a multple of res.
            res: The number of periods of noise to generate along each
                axis (tuple of two ints). Note shape must be a multiple of
                res.
            tileable: If the noise should be tileable along each axis
                (tuple of two bools). Defaults to (False, False).
            interpolant: The interpolation function, defaults to
                t*t*t*(t*(t*6 - 15) + 10).
        Returns:
            A numpy array of shape shape with the generated noise.
        Raises:
            ValueError: If shape is not a multiple of res.
        """
        if interpolant == None:
            interpolant = self.interpolant
        delta = (res[0] / shape[0], res[1] / shape[1])
        d = (shape[0] // res[0], shape[1] // res[1])
        grid = np.mgrid[0:res[0]:delta[0], 0:res[1]:delta[1]].transpose(1, 2, 0) % 1
        # Gradients
        #angles = 2*np.pi*np.random.rand(res[0]+1, res[1]+1)
        angles = 2*np.pi*self.rng.random((res[0]+1, res[1]+1))
        gradients = np.dstack((np.cos(angles), np.sin(angles)))
        if tileable[0]:
            gradients[-1,:] = gradients[0,:]
        if tileable[1]:
            gradients[:,-1] = gradients[:,0]
        gradients = gradients.repeat(d[0], 0).repeat(d[1], 1)
        g00 = gradients[    :-d[0],    :-d[1]]
        g10 = gradients[d[0]:     ,    :-d[1]]
        g01 = gradients[    :-d[0],d[1]:     ]
        g11 = gradients[d[0]:     ,d[1]:     ]
        # Ramps
        n00 = np.sum(np.dstack((grid[:,:,0]  , grid[:,:,1]  )) * g00, 2)
        n10 = np.sum(np.dstack((grid[:,:,0]-1, grid[:,:,1]  )) * g10, 2)
        n01 = np.sum(np.dstack((grid[:,:,0]  , grid[:,:,1]-1)) * g01, 2)
        n11 = np.sum(np.dstack((grid[:,:,0]-1, grid[:,:,1]-1)) * g11, 2)
        # Interpolation
        t = interpolant(grid)
        n0 = n00*(1-t[:,:,0]) + t[:,:,0]*n10
        n1 = n01*(1-t[:,:,0]) + t[:,:,0]*n11
        return np.sqrt(2)*((1-t[:,:,1])*n0 + t[:,:,1]*n1)


    def generate_fractal_noise_2d( self,
            shape, res, octaves=1, persistence=0.5,
            lacunarity=2, tileable=(False, False),
            interpolant=interpolant
            ):
        """Generate a 2D numpy array of fractal noise.
        Args:
            shape: The shape of the generated array (tuple of two ints).
                This must be a multiple of lacunarity**(octaves-1)*res.
            res: The number of periods of noise to generate along each
                axis (tuple of two ints). Note shape must be a multiple of
                (lacunarity**(octaves-1)*res).
            octaves: The number of octaves in the noise. Defaults to 1.
            persistence: The scaling factor between two octaves.
            lacunarity: The frequency factor between two octaves.
            tileable: If the noise should be tileable along each axis
                (tuple of two bools). Defaults to (False, False).
            interpolant: The, interpolation function, defaults to
                t*t*t*(t*(t*6 - 15) + 10).
        Returns:
            A numpy array of fractal noise and of shape shape generated by
            combining several octaves of perlin noise.
        Raises:
            ValueError: If shape is not a multiple of
                (lacunarity**(octaves-1)*res).
        """
        noise = np.zeros(shape)
        frequency = 1
        amplitude = 1
        for _ in range(octaves):
            noise += amplitude * self.generate_perlin_noise_2d(
                shape, (frequency*res[0], frequency*res[1]), tileable, self.interpolant
            )
            frequency *= lacunarity
            amplitude *= persistence
        return noise
    #endregion Perlin Noise

#endregion Interactive Terrain


#region  main


# Function to put instructions on the screen.
def addInstructions(pos, msg):
    return OnscreenText(text = msg, style = 1, fg = (1, 1, 1, 1), 
                        pos = (-0.9, pos - 0.2), align = p3dc.TextNode.ALeft, scale = .035)

class scene(ape.APEScene):
    def start(self):
        ape.base().start()

class EngineClass(ape.APE):
    def start(self):
        self.Scene = scene()
        self.Scene.start()

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
        
        self.genCB = QtWidgets.QCheckBox(self)
        self.genCB.setText("Use seed 6")
        genLayout.addWidget(self.genCB)
        self.genButton = AGeWidgets.Button(self,"Reload code and run",self.gen)
        genLayout.addWidget(self.genButton)
        
        self.genWidget.setLayout(genLayout)
        layout.addWidget(self.genWidget)
        
        self.cw.setLayout(layout)
    
    def gen(self):
        if self.genCB.isChecked():
            App().base.reload(seed = 6)
        else:
            App().base.reload()

class PandaWidget(ape.PandaWidget):
    pass




#endregion real main
if __name__ == '__main__':
    ape.start(WindowTitle, EngineClass, InteractiveTerrain, AppClass, MainWindowClass, PandaWidget, True, SupportsRenderPipeline)
