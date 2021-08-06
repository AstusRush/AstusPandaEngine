SupportsRenderPipeline = False
#region imports
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
#import inspect
import io
import PIL

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
from AstusPandaEngine import Classes as apec # pylint: disable = import-error

sys.path.insert(0, "../tobsprRenderPipeline")
sys.path.insert(0, "tobsprRenderPipeline")
# Import render pipeline classes
from tobsprRenderPipeline import rpcore # pylint: disable = import-error

sys.path.append('..')
#endregion imports

#region gen_o

def gen_o_1(self, rows = 600, cols = 300, seed = 0):
    if rows < cols:
        rows, cols = cols, rows
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
    return seed
    #endregion What is done here?

def gen_o_2(self, rows = 600, cols = 300, seed = 0):
    if rows < cols:
        rows, cols = cols, rows
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
    
    mode = 3
    
    pz = [rng.uniform(-1,1)]
    for i in range(rows):
        pz.append(rng.uniform(pz[i-1]-1,pz[i]+1))
    for y in range(0,rows):
        for x in range(0,cols):
            nz1 = rng.uniform(pz[x]   - 1, pz[x]   + 1)
            nz2 = rng.uniform(pz[x-1] - 1, pz[x-1] + 1)
            nz3 = rng.uniform(pz[x+1] - 1, pz[x+1] + 1)
            nz = (nz1 + nz2 + nz3) / 3
            if mode == 1 or mode == 3:
                self.vertex.add_data3f((x, y+1, nz   ))
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
            
            if mode == 2 or mode == 3:
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
            
            pz[x] = nz

    geom = p3dc.Geom(self.vdata)
    for y in range(0, rows):
        prim = p3dc.GeomTristrips(p3dc.Geom.UH_static)
        if mode == 3:
            prim.addVertex(y*cols*2)
            prim.add_next_vertices((cols*2)-1)
        else:
            prim.addVertex(y*cols)
            prim.add_next_vertices((cols)-1)
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
    return seed
    #endregion What is done here?

#endregion gen_o
#region gen

def gen_1(self, rows = 300, cols = 600, seed = 0):
    # Ensure that "power of 2" thing https://docs.panda3d.org/1.10/python/programming/terrain/geometrical-mipmapping#basic-usage #TODO: Improve this comment
    rowsBin, colsBin = 2**8+1, 2**8+1
    seed = int(seed)
    if not seed:
        seed = self.seedGen.integers(1000000)
    self.rng = np.random.default_rng(seed)
    mat = mat_6(self, rowsBin, colsBin)
    col = col_4(self, mat)
    lit_3(self,mat)
    Water_3(self,mat)
    fin_4(self,mat,col)#
    #fin_1(self,mat,col)
    self.terrainMatrix = mat
    self.terrainColourMatrix = col
    return seed

#endregion gen
#region mat

def mat_1(self, rows, cols): # Zero
    #
    mat = np.zeros((rows,cols))
    return mat

def mat_2(self, rows, cols): # Completely random
    #
    mat = self.rng.uniform( 0,7 , (rows,cols))
    return mat

def mat_3(self, rows, cols): # Landscape 1 V1
    mat = np.zeros((rows,cols))
    rows, cols = cols, rows
    pz = [self.rng.uniform(-1,1)]
    for i in range(rows):
        pz.append(self.rng.uniform(pz[i-1]-1,pz[i]+1))
    for y in range(0,rows):
        for x in range(0,cols):
            nz1 = self.rng.uniform(pz[x]   - 1, pz[x]   + 1)
            nz2 = self.rng.uniform(pz[x-1] - 1, pz[x-1] + 1)
            nz3 = self.rng.uniform(pz[x+1] - 1, pz[x+1] + 1)
            nz = (nz1 + nz2 + nz3) / 3
            #mat[x, y+1] = nz    #
            mat[x, y  ] = pz[x] #
            pz[x] = nz
    #
    return mat

def mat_4(self, rows, cols): # Landscape 1 V2 #TODO: Make a V2. This is currently a copy of V1...
    mat = np.zeros((rows,cols))
    rows, cols = cols, rows
    pz = [self.rng.uniform(-1,1)]
    for i in range(rows):
        pz.append(self.rng.uniform(pz[i-1]-1,pz[i]+1))
    for y in range(0,rows):
        for x in range(0,cols):
            nz1 = self.rng.uniform(pz[x]   - 1, pz[x]   + 1)
            nz2 = self.rng.uniform(pz[x-1] - 1, pz[x-1] + 1)
            nz3 = self.rng.uniform(pz[x+1] - 1, pz[x+1] + 1)
            nz = (nz1 + nz2 + nz3) / 3
            #mat[x, y+1] = nz    #
            mat[x, y  ] = pz[x] #
            pz[x] = nz
    #
    return mat

def mat_5(self, rows, cols): # Perlin Noise
    c = max(rows,cols)+100-max(rows,cols)%100
    return self.generate_fractal_noise_2d((c,c),(4,4))[:rows,:cols]*10

def mat_6(self, rows, cols): # Perlin Noise 2
    c = max(rows,cols)+100-max(rows,cols)%100
    mat =  self.generate_fractal_noise_2d((c,c),(5,5))*10
    mat += self.generate_fractal_noise_2d((c,c),(2,2))*10
    mat += self.generate_fractal_noise_2d((c,c),(20,20))*2
    mat += self.generate_fractal_noise_2d((c,c),(100,100))*0.7
    return mat[:rows,:cols]

#endregion mat
#region col

def col_1(self, mat): # White
    col = np.ones((mat.shape[0], mat.shape[1], 4))
    return col

def col_2(self, mat): # Orange
    col = np.zeros((mat.shape[0], mat.shape[1], 4))
    col[:,:,3] = 1
    # Orange
    col[:,:,0] = 1
    col[:,:,1] = 0.5
    return col

def col_3(self, mat): # Landscape 1
    col = np.zeros((mat.shape[0], mat.shape[1]  , 4))
    col[:,:,3] = 1
    ###
    i = 4.5 #if mat >= i:   # 2
    colour = (1  , 1  , 1  , 1)
    np.putmask(col[:,:,0],mat>=i, colour[0])
    np.putmask(col[:,:,1],mat>=i, colour[1])
    np.putmask(col[:,:,2],mat>=i, colour[2])
    ###
    #     #if mat < i:   # 2
    colour = (0.4, 0.4, 0.4, 1)
    np.putmask(col[:,:,0],mat< i, colour[0])
    np.putmask(col[:,:,1],mat< i, colour[1])
    np.putmask(col[:,:,2],mat< i, colour[2])
    ###
    i = 1 #if mat < i:   # 0
    colour = (0  , 0.4, 0.2, 1)
    np.putmask(col[:,:,0],mat< i, colour[0])
    np.putmask(col[:,:,1],mat< i, colour[1])
    np.putmask(col[:,:,2],mat< i, colour[2])
    ###
    i = -3 #if mat < i:   # -3
    colour = (0  , 0.2, 0.1, 1)
    np.putmask(col[:,:,0],mat< i, colour[0])
    np.putmask(col[:,:,1],mat< i, colour[1])
    np.putmask(col[:,:,2],mat< i, colour[2])
    ###
    i = -5 #if mat < i:   # -5
    colour = (0  , 0.1, 0.5, 1) # (0.2, 0.1, 0  , 1)
    np.putmask(col[:,:,0],mat< i, colour[0])
    np.putmask(col[:,:,1],mat< i, colour[1])
    np.putmask(col[:,:,2],mat< i, colour[2])
    return col

def col_4(self, mat): # Landscape 1
    def putColour(colourMatrix, mask, colour):
        np.putmask(colourMatrix[:,:,0], mask, colour[0])
        np.putmask(colourMatrix[:,:,1], mask, colour[1])
        np.putmask(colourMatrix[:,:,2], mask, colour[2])
    col = np.ones((mat.shape[0], mat.shape[1]  , 4))
    #np.putmask(col, mat >=4.5 , ( 1  , 1  , 1   ))
    putColour(col, mat < 4.5 , ( 0.4, 0.4, 0.4 ))
    putColour(col, mat < 1   , ( 0  , 0.4, 0.2 ))
    putColour(col, mat < -3  , ( 0  , 0.2, 0.1 ))
    putColour(col, mat < -5  , ( 0  , 0.1, 0.5 )) #CRITICAL: Revert this to ( 0  , 0.1, 0.5 ) or choose a sand colour
    return col

#endregion col
#region lit

def lit_o_1(self, mat):
    #region Create point lights #TODO: Rework and improve
    #IMPROVE: self.plights should be used from the beginning
    plights = []
    
    for i in range(0,int(mat.shape[1]/5),2):
        plight = p3dc.PointLight("plight")
        plight.setColor(p3dc.VBase4(1, 1, 1, 1))
        #IMPROVE: The next line is superfluous and the line after that should use append
        plights.append(plight)
        plights[i] = self.render.attachNewNode(plight)
        x,y,_ = self.camera.get_pos()
        plights[i].setPos(mat.shape[1]/2+((i-int(i/2))*10),y+20,5)
        self.render.set_light(plights[i])
        
        #CLEANUP: reduce code duplication
        plight = p3dc.PointLight("plight")
        plight.setColor(p3dc.VBase4(1, 1, 1, 1))
        #IMPROVE: The next line is superfluous and the line after that should use append
        plights.append(plight)
        plights[i+1] = self.render.attachNewNode(plight)
        x,y,_ = self.camera.get_pos()
        plights[i+1].setPos(mat.shape[1]/2+((i-int(i/2))*10),y+20,10)
        self.render.set_light(plights[i+1])
    
    self.plights = plights #CLEANUP: replace plights with self.plights
    #endregion Create point lights

def lit_1(self, mat):
    #IMPROVE: self.plights should be used from the beginning
    self.plights = []
    self.render.clearLight()
    plights = []
    i=0
    n=0
    c = [p3dc.VBase4(1,n,n,1),p3dc.VBase4(n,1,n,1),p3dc.VBase4(n,n,1,1)]
    w = p3dc.VBase4(1,1,1,1)
    for x in range(int(mat.shape[0]*1/10),int(mat.shape[0]*9/10),100):
        for y in range(int(mat.shape[1]*1/10),int(mat.shape[1]*9/10),100):
            plight = p3dc.PointLight("plight")
            plight.setColor(w)#(c[i%3])
            plights.append(plight)
            plights[-1] = self.render.attachNewNode(plight)
            plights[-1].setPos((x,y,30))
            self.render.set_light(plights[-1])
            print((x,y,10))
            i+=1
    
    self.plights = plights #CLEANUP: replace plights with self.plights
    
def lit_2(self, mat):
    #IMPROVE: self.plights should be used from the beginning
    def separate(length,steps=4):
        stepSize = length/(steps)
        start = stepSize/2
        a = []
        for i in range(0,steps):
            a.append(start+i*stepSize)
        return a

    plights = []
    if self.render_pipeline:
        try:
            for i in self.plights:
                try:
                    self.render_pipeline.remove_light(i)
                except:
                    pass
        except:
            pass
        self.plights = []
        n=0
        f=0.2
        c = [(f,n,n),(n,f,n),(n,n,f)]
        w = (1,1,1)
        i=0
        for x in separate(mat.shape[0],2):
            for y in separate(mat.shape[1],4):
                plight = rpcore.PointLight()
                plight.color = w#c[(i)%3] #(0.2, 0.6, 1.0)#
                plight.casts_shadows = True
                plight.pos = (x,y,20)
                plight.energy = 10000.0
                plight.radius = 100
                plight.shadow_map_resolution = 512
                plight.near_plane = 0.2
                plight.ies_profile = self.render_pipeline.load_ies_profile("x_arrow.ies")
                #plight.set_color_from_temperature(1000.0)
                plights.append(plight)
                self.render_pipeline.add_light(plights[-1])
                i+=1
    else:
        self.plights = []
        self.render.clearLight()
        n=0
        c = [(1,n,n,1),(n,1,n,1),(n,n,1,1)]
        w = (1,1,1,1)
        i=0
        for x in separate(mat.shape[0],2):
            for y in separate(mat.shape[1],4):
                plight = p3dc.PointLight("plight")
                plight.setColor(c[(i)%3])
                plights.append(plight)
                plights[-1] = self.render.attachNewNode(plight)
                plights[-1].setPos((x,y,30))
                self.render.set_light(plights[-1])
                i+=1
    
    self.plights = plights #CLEANUP: replace plights with self.plights
    
def lit_3(self, mat):
    def separate(length,steps=4):
        stepSize = length/(steps)
        start = stepSize/2
        a = []
        for i in range(0,steps):
            a.append(start+i*stepSize)
        return a
    
    ape.lightManager().purgeLights()
    self.lights = []
    
    n = 0
    f = 0.3
    c = [(f,n,n),(n,f,n),(n,n,f)]
    w = (1,1,1)
    i=0
    for x in separate(mat.shape[0],2):
        for y in separate(mat.shape[1],4):
            self.lights.append(ape.lightManager().addPointLight((x,y,mat[int(x),int(y)]+5),w))
            #self.lights.append(ape.lightManager().addPointLight((x,y,mat[int(x),int(y)]+5),c[(i)%3]))
            i+=1

#endregion lit
#region Water
def Water_1(self, mat):
    col = np.zeros((mat.shape[0], mat.shape[1], 4))
    col[:,:,3] = 0.2
    # Blue
    col[:,:,1] = 0.1
    col[:,:,2] = 0.5
    #
    surface = np.zeros_like(mat)
    hMap = PIL.Image.fromarray(np.uint8(surface), 'L')
    cMap = PIL.Image.fromarray(np.uint8(col*255), 'RGBA')
    hBuf = io.BytesIO()
    hMap.save(hBuf, format="png")
    hiMap = p3dc.PNMImage()
    hiMap.read(p3dc.StringStream(hBuf.getvalue()),"t.png")
    ciMap = p3dc.PNMImage()
    cBuf = io.BytesIO()
    cMap.save(cBuf, format="png")
    ciMap = p3dc.PNMImage()
    ciMap.read(p3dc.StringStream(cBuf.getvalue()),"t.png")
    NC(10,ciMap.get_alpha(3,3))
    try:
        self.WaterSurface.setHeightfield(hiMap)
    except:
        self.WaterSurface = p3dc.GeoMipTerrain("WaterSurface")
        self.WaterSurface.setHeightfield(hiMap)
    self.WaterSurface.setColorMap(ciMap)
    self.WaterSurface.getRoot().setSz(0.1)
    #self.WaterSurface.setBruteforce(True)
    self.WaterSurface.getRoot().reparentTo(self.render)
    self.WaterSurface.getRoot().setPos((0,0,-5))
    self.WaterSurface.generate()
    
def Water_2(self, mat):
    try:
        self.WaterSurfaceCard.removeNode()
        del self.WaterSurfaceCard
    except AttributeError:
        NC(4,"could not delete WaterSurfaceCard",exc=True)
    except:
        NC(3,"could not delete WaterSurfaceCard",exc=True)
    cm = p3dc.CardMaker("WaterSurfaceCard")
    z = -5
    p1 = (0,0,z)
    p4 = (0,mat.shape[1],z)
    p2 = (mat.shape[0],0,z)
    p3 = (mat.shape[0],mat.shape[1],z)
    cm.set_frame(p1,p2,p3,p4)
    #cm.setColor((0,0.1,0.5,0.2))
    cm.setColor((0,0.1,1,0.7))
    self.WaterSurfaceCard = self.render.attachNewNode(cm.generate())
    self.WaterSurfaceCard.setTransparency(p3dc.TransparencyAttrib.MAlpha)
    
def Water_3(self, mat):
    try:
        self.WaterSurfaceCard.removeNode()
        del self.WaterSurfaceCard
    except AttributeError:
        NC(4,"could not delete WaterSurfaceCard",exc=True)
    except:
        NC(3,"could not delete WaterSurfaceCard",exc=True)
    cm = p3dc.CardMaker("WaterSurfaceCard")
    z = -5
    p1 = (0,0,z)
    p4 = (0,mat.shape[1],z)
    p2 = (mat.shape[0],0,z)
    p3 = (mat.shape[0],mat.shape[1],z)
    cm.set_frame(p1,p2,p3,p4)
    #cm.setColor((0,0.1,0.5,0.2))
    #cm.setColor((0,0.1,1,0.7))
    self.WaterSurfaceCard = self.render.attachNewNode(cm.generate())
    #
    col = np.zeros((mat.shape[0], mat.shape[1], 4))
    col[:,:,3] = 0.79
    # Blue
    col[:,:,1] = 0.1
    col[:,:,2] = 1
    #
    cMap = PIL.Image.fromarray(np.uint8(col*255), 'RGBA')
    ciMap = p3dc.PNMImage()
    cBuf = io.BytesIO()
    cMap.save(cBuf, format="png")
    ciMap = p3dc.PNMImage()
    ciMap.read(p3dc.StringStream(cBuf.getvalue()),"t.png")
    NC(10,ciMap.get_alpha(3,3))
    #self.WaterSurfaceCard.
    panda_tex = p3dc.Texture("default")
    panda_tex.load(ciMap)
    panda_mat = p3dc.Material("default")
    #panda_mat.emission = 0
    #panda_mat.setEmission((0.1,0.1,0.1,1))
    
    self.WaterSurfaceCard.setTransparency(p3dc.TransparencyAttrib.MAlpha)
    self.WaterSurfaceCard.set_material(panda_mat)
    self.WaterSurfaceCard.set_texture(panda_tex)
    #if self.render_pipeline:
        # Set time of day
        #self.render_pipeline.daytime_mgr.time = "0:40"
        #self.render_pipeline.daytime_mgr.time = "7:40"
        #self.render_pipeline.daytime_mgr.time = "13:40"
        
        # Use a special effect for rendering the scene.
        # This is necessary because there are no normals or valid materials.
        #self.render_pipeline.set_effect(ape.render(), "_pipeline_effect-vertex-colour.yaml", {
        #    #"render_gbuffer": True,
        #    ##"render_forward": False,
        #    "render_shadow": True,
        #    ##"alpha_testing": False,
        #    #"normal_mapping": True,
        #    #"render_voxel": True,
        #    #"render_envmap": True,
        #    }, sort=250)
        #self.render_pipeline.prepare_scene(self.render)

#endregion Water
#region fin

def fin_1(self, mat, col): # Tristrips
    #region
    Format = p3dc.GeomVertexFormat.getV3c4()
    self.vdata = p3dc.GeomVertexData('name', Format, p3dc.Geom.UHStatic)
    self.vdata.setNumRows(mat.size)
    self.vertex = p3dc.GeomVertexWriter(self.vdata, 'vertex')
    self.color = p3dc.GeomVertexWriter(self.vdata, 'color')
    
    for y in range(0, mat.shape[1]-1):
        for x in range(0, mat.shape[0]):
            self.vertex.add_data3f((x  ,y+1,mat[x  ,y+1]))
            self.color.add_data4f(    tuple(col[x  ,y+1]))
            self.vertex.add_data3f((x  ,y  ,mat[x  ,y  ]))
            self.color.add_data4f(    tuple(col[x  ,y  ]))
    
    geom = p3dc.Geom(self.vdata)
    for y in range(0, mat.shape[1]-1):
        prim = p3dc.GeomTristrips(p3dc.Geom.UH_static)
        prim.addVertex(y*mat.shape[0]*2)
        prim.add_next_vertices((mat.shape[0]*2)-1)
        prim.close_primitive()
        geom.addPrimitive(prim)

    nodeTris = p3dc.GeomNode("terrain")
    nodeTris.addGeom(geom)
    try:
        self.nodeTrisPath.removeNode()
        del self.nodeTrisPath
    except AttributeError:
        NC(4,"could not delete nodeTrisPath",exc=True)
    except:
        NC(3,"could not delete nodeTrisPath",exc=True)
    self.nodeTrisPath = self.render.attachNewNode(nodeTris)
    #panda_mat = p3dc.Material("default")
    #panda_mat.emission = 0
    #self.nodeTrisPath.set_material(panda_mat)
    #endregion
    if self.render_pipeline:
        # Set time of day
        #self.render_pipeline.daytime_mgr.time = "7:40"
        #self.render_pipeline.daytime_mgr.time = "0:40"
        #self.render_pipeline.daytime_mgr.time = "13:40"
        
        # Use a special effect for rendering the scene.
        # This is necessary because there are no normals or valid materials.
        self.render_pipeline.set_effect(ape.render(), "_pipeline_effect-vertex-colour.yaml", {
            #"render_gbuffer": True,
            ##"render_forward": False,
            #"render_shadow": True,
            ##"alpha_testing": False,
            #"normal_mapping": True,
            #"render_voxel": True,
            #"render_envmap": True,
            }, sort=250)
        self.render_pipeline.prepare_scene(self.nodeTrisPath)

def fin_2(self, mat, col): # Triangles # TOO SLOW
    #region
    Format = p3dc.GeomVertexFormat.getV3c4()
    self.vdata = p3dc.GeomVertexData('name', Format, p3dc.Geom.UHStatic)
    self.vdata.setNumRows(mat.size)
    self.vertex = p3dc.GeomVertexWriter(self.vdata, 'vertex')
    self.color = p3dc.GeomVertexWriter(self.vdata, 'color')
    
    for x in range(0, mat.shape[0]-1):
        for y in range(0, mat.shape[1]-1):
            self.vertex.add_data3f((x  ,y  ,mat[x  ,y  ]))
            self.color.add_data4f(    tuple(col[x  ,y  ]))
            self.vertex.add_data3f((x+1,y  ,mat[x+1,y  ]))
            self.color.add_data4f(    tuple(col[x+1,y  ]))
            self.vertex.add_data3f((x  ,y+1,mat[x  ,y+1]))
            self.color.add_data4f(    tuple(col[x  ,y+1]))
            
            self.vertex.add_data3f((x  ,y+1,mat[x  ,y+1]))
            self.color.add_data4f(    tuple(col[x  ,y+1]))
            self.vertex.add_data3f((x+1,y  ,mat[x+1,y  ]))
            self.color.add_data4f(    tuple(col[x+1,y  ]))
            self.vertex.add_data3f((x+1,y+1,mat[x+1,y+1]))
            self.color.add_data4f(    tuple(col[x+1,y+1]))
    
    geom = p3dc.Geom(self.vdata)
    for i in range(0, (mat.shape[0]-1)*(mat.shape[1]-1)):
        prim = p3dc.GeomTriangles(p3dc.Geom.UH_static)
        prim.addVertex(i*3)
        prim.add_next_vertices(i*3+2)
        prim.close_primitive()
        geom.addPrimitive(prim)

    nodeTris = p3dc.GeomNode("terrain")
    nodeTris.addGeom(geom)
    try:
        self.nodeTrisPath.removeNode()
        del self.nodeTrisPath
    except AttributeError:
        NC(4,"could not delete nodeTrisPath",exc=True)
    except:
        NC(3,"could not delete nodeTrisPath",exc=True)
    self.nodeTrisPath = self.render.attachNewNode(nodeTris)
    #endregion

def fin_3(self, mat, col): # Heightfield Tesselator #TODO
    # Link to Panda3D Terrain Docs https://docs.panda3d.org/1.10/python/programming/terrain/index
    # https://docs.panda3d.org/1.10/python/programming/terrain/heightfield-tesselator#heightfield-tesselator
    pass

def fin_4(self, mat, col): # Geometrical MipMapping
    # Link to Panda3D Terrain Docs https://docs.panda3d.org/1.10/python/programming/terrain/index
    # https://docs.panda3d.org/1.10/python/programming/terrain/geometrical-mipmapping#geometrical-mipmapping
    #
    # https://docs.panda3d.org/1.10/python/programming/terrain/geometrical-mipmapping#basic-usage
    # Maybe: https://docs.panda3d.org/1.10/python/programming/internal-structures/other-manipulation/creating-textures#creating-new-textures-from-scratch
    #
    try:
        self.nodeTrisPath.removeNode()
        del self.nodeTrisPath
    except AttributeError:
        NC(4,"could not delete nodeTrisPath",exc=True)
    except:
        NC(3,"could not delete nodeTrisPath",exc=True)
    hMap = PIL.Image.fromarray(np.uint8(np.flip(((mat-mat.min())/(mat.max()-mat.min())),(1)).T * 255) , 'L')
    #cMap = PIL.Image.fromarray(np.uint8(col.transpose(1,0,2)*255),'RGBA')
    cMap = PIL.Image.fromarray(np.uint8((np.flip(col,(1)).transpose(1,0,2))*255),'RGBA')
    hBuf = io.BytesIO()
    hMap.save(hBuf, format="png")
    hiMap = p3dc.PNMImage()
    hiMap.read(p3dc.StringStream(hBuf.getvalue()),"t.png")
    ciMap = p3dc.PNMImage()
    cBuf = io.BytesIO()
    cMap.save(cBuf, format="png")
    ciMap = p3dc.PNMImage()
    ciMap.read(p3dc.StringStream(cBuf.getvalue()),"t.png")
    try:
        self.terrain.setHeightfield(hiMap)
    except:
        self.terrain = p3dc.GeoMipTerrain("terrain")
        self.terrain.setHeightfield(hiMap)
    #self.terrain.setColorMap(ciMap)
    self.terrain.getRoot().setSz(mat.max()-mat.min())
    #self.terrain.setBruteforce(True)
    self.terrain.getRoot().reparentTo(self.render)
    self.terrain.getRoot().setPos((0,0,mat.min()))
    panda_tex = p3dc.Texture("default")
    panda_tex.load(ciMap)
    panda_mat = p3dc.Material("default")
    #panda_mat.emission = 0
    panda_mat.setEmission((0.1,0.1,0.1,1))
    self.terrain.getRoot().set_material(panda_mat)
    self.terrain.getRoot().set_texture(panda_tex)
    self.terrain.generate()
    #if self.render_pipeline:
        # Set time of day
        #self.render_pipeline.daytime_mgr.time = "0:40"
        #self.render_pipeline.daytime_mgr.time = "4:40"
        #self.render_pipeline.daytime_mgr.time = "5:20"
        #self.render_pipeline.daytime_mgr.time = "7:40"
        #self.render_pipeline.daytime_mgr.time = "13:40"
        
        # Use a special effect for rendering the scene.
        # This is necessary because there are no normals or valid materials.
        #self.render_pipeline.set_effect(ape.render(), "_pipeline_effect-vertex-colour.yaml", {
        #    #"render_gbuffer": True,
        #    ##"render_forward": False,
        #    "render_shadow": True,
        #    ##"alpha_testing": False,
        #    #"normal_mapping": True,
        #    #"render_voxel": True,
        #    #"render_envmap": True,
        #    }, sort=250)
        #self.render_pipeline.prepare_scene(self.render) #TODO: Make this work

def fin_5(self, mat, col): # ShaderTerrainMesh #TODO
    # Link to Panda3D Terrain Docs https://docs.panda3d.org/1.10/python/programming/terrain/index
    # https://docs.panda3d.org/1.10/python/reference/panda3d.core.ShaderTerrainMesh#panda3d.core.ShaderTerrainMesh
    pass

#endregion fin
gen = gen_1

