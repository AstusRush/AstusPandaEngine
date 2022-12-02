SupportsRenderPipeline = False

import datetime
import platform
WindowTitle = "APE-Procedural-Terrain-1-Static-Example"
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

class Grid(ape.APEPandaBase): #DEPRECATED
    #FEATURE: Move the generation into a method and add a button that calls the method with optional seed (and maybe size (limit max size!)).
    #           The Method also needs to remove the previous terrain and clean up the memory.
    def start(self):
        if self.render_pipeline:
            # Set time of day
            self.render_pipeline.daytime_mgr.time = "7:40"
            
            # Use a special effect for rendering the scene.
            # This is necessary because there are no normals or valid materials.
            self.render_pipeline.set_effect(ape.render(), "_pipeline_effect-vertex-colour.yaml", {}, sort=250)

        # Set size
        self.cols = 300
        self.rows = 600
        
        # Set up camera #TODO: Improve camera behaviour by creating own 
        base().setFrameRateMeter(True)
        #base().disableMouse()
        
        base().trackball.node().set_pos(-12,0,-12)
        
        #Following does not work
        #base().trackball.set_pos(-120,0,-12)
        #base().trackball.setP(5)
        #base().trackball.look_at(self.cols/2,300,0)
        
        #base().enableMouse()


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

    def moveForwardTask(self,task): #CLEANUP: Remove
        change = 0.7
        self.counter = self.counter+change
        x,y,z = self.camera.get_pos()
        self.camera.set_pos(x,y+change,z)
        for i in range(0,len(self.plights)):
            x,y,z = self.plights[i].get_pos()
            self.plights[i].set_pos(x,y+change,z)
            self.render.set_light(self.plights[i])

        if y > self.rows1:
            self.nodeTrisPath.removeNode()

        if self.counter >= 1:
            if y > self.rows1:
                self.newNodePath[0].removeNode()
                del self.newNodePath[0]
            self.counter = self.counter - 1
            for x in range(0, self.cols):
                nz1 = random.uniform(self.pz[x] - 1, self.pz[x] + 1)
                nz2 = random.uniform(self.pz[x - 1] - 1, self.pz[x - 1] + 1)
                nz3 = random.uniform(self.pz[x + 1] - 1, self.pz[x + 1] + 1)
                nz = (nz1 + nz2 + nz3) / 3
                self.vertex.add_data3f((x, self.rows + 1, nz))
                self.vertex.add_data3f((x, self.rows, self.pz[x]))
                if nz < -5:
                    self.color.add_data4f(0.2, 0.1, 0, 1)
                elif nz < -3:
                    self.color.add_data4f(0, 0.2, 0.1, 1)
                elif nz < 0:
                    self.color.add_data4f(0, 0.4, 0.2, 1)
                elif nz < 4:
                    self.color.add_data4f(0.4, 0.4, 0.4, 1)
                else:
                    self.color.add_data4f(1, 1, 1, 1)
                if nz < -5:

                    self.color.add_data4f(0.2, 0.1, 0, 1)
                elif nz < -3:
                    self.color.add_data4f(0, 0.2, 0.1, 1)
                elif self.pz[x] < 0:
                    self.color.add_data4f(0, 0.4, 0.2, 1)
                elif self.pz[x] < 4:
                    self.color.add_data4f(0.4, 0.4, 0.4, 1)
                else:
                    self.color.add_data4f(1, 1, 1, 1)
                self.pz[x] = nz
                #print(nz)
            geom = p3dc.Geom(self.vdata)
            prim = p3dc.GeomTristrips(p3dc.Geom.UH_static)
            prim.addVertex(self.cols*2*self.rows)
            prim.add_next_vertices((self.cols*2)-1)
            prim.close_primitive()
            geom.addPrimitive(prim)
            node = p3dc.GeomNode("TriStrips")
            node.addGeom(geom)
            self.newNodePath.append(self.render.attachNewNode(node))
            self.rows = self.rows + 1
        return Task.cont


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
        if interpolant is None:
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

#region    real main


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

class MainWindowClass(ape.APEWindow):
    #TODO: Make a window in which the code for the makeTerrain_temp can be entered to modify the algorithm during runtime
    # ape.base().get_code       can be used to get the current code
    # ape.base().apply_code     currently executes the code but a way to actually apply the code is still necessary
    # Furthermore a way to call makeTerrain_temp would be handy
    # Maybe even make a function selection and save the sourcecode so that it can be loaded. And allow for different versions.
    #       Something like the colour palettes but for code...
    #
    # Or we just use a different file and reload it with a button
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
            App().base.g(seed = 6)
        else:
            App().base.g()

class PandaWidget(ape.PandaWidget):
    pass




#endregion real main
if __name__ == '__main__':
    #ape.start(WindowTitle, EngineClass, terrainGenDemo, AppClass, MainWindowClass, PandaWidget, True, SupportsRenderPipeline)
    #ape.start(WindowTitle, EngineClass, Grid, AppClass, MainWindowClass, PandaWidget, True, SupportsRenderPipeline)
    ape.start(WindowTitle, EngineClass, Terrain, AppClass, MainWindowClass, PandaWidget, True, SupportsRenderPipeline)
