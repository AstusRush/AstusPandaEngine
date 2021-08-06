# Adaptation from https://github.com/OwenPauptit/Panda3D-ProceduralTerrainGeneration by OwenPauptit

SupportsRenderPipeline = False

import datetime
import platform
WindowTitle = "APE-Procedural-Terrain-1-Endless-Example"
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

sys.path.append('..')

############################################

class Grid(ape.APEPandaBase):
    def start(self):
        if self.render_pipeline:
            # Set time of day
            self.render_pipeline.daytime_mgr.time = "7:40"
            
            # Use a special effect for rendering the scene.
            # This is necessary because there are no normals or valid materials.
            self.render_pipeline.set_effect(ape.render(), "_pipeline_effect-vertex-colour.yaml", {}, sort=250)

        self.cols = 300
        self.rows = 600

        base().disableMouse()
        base().setFrameRateMeter(True)
        self.cameraHeight = 13
        self.camera.set_pos(self.cols/2,-30,self.cameraHeight)
        self.camera.look_at(self.cols/2,300,0)

        plights = []

        for i in range(0,int(self.cols/5),2):
            plight = p3dc.PointLight("plight")
            plight.setColor(p3dc.VBase4(1, 1, 1, 1))
            plights.append(plight)
            plights[i] = self.render.attachNewNode(plight)
            x,y,_ = self.camera.get_pos()
            plights[i].setPos(self.cols/2+((i-int(i/2))*10),y+20,5)
            self.render.set_light(plights[i])

            plight = p3dc.PointLight("plight")
            plight.setColor(p3dc.VBase4(1, 1, 1, 1))
            plights.append(plight)
            plights[i+1] = self.render.attachNewNode(plight)
            x,y,_ = self.camera.get_pos()
            plights[i+1].setPos(self.cols/2+((i-int(i/2))*10),y+20,10)
            self.render.set_light(plights[i+1])

        self.plights = plights

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
                nz1 = random.uniform(pz[x]-1,pz[x]+1)
                nz2 =random.uniform(pz[x-1]-1,pz[x-1]+1)
                nz3 = random.uniform(pz[x+1] - 1, pz[x + 1] + 1)
                nz = (nz1 + nz2 + nz3) / 3
                self.vertex.add_data3f((x,y+1,nz))
                self.vertex.add_data3f((x,y,pz[x]))
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
                    self.color.add_data4f(0.2, 0.1, 0, 1)
                elif nz < -3:
                    self.color.add_data4f(0, 0.2, 0.1,1)
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
        self.task_mgr.add(self.moveForwardTask,"moveForwardTask")

        self.vdata = vdata
        self.newNodePath = []
        self.counter = 0
        self.rows1 = self.rows

    def moveForwardTask(self,task):
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
            prim.add_next_vertices((self.cols * 2)-1)
            prim.close_primitive()
            geom.addPrimitive(prim)
            node = p3dc.GeomNode("TriStrips")
            node.addGeom(geom)
            self.newNodePath.append(self.render.attachNewNode(node))
            self.rows = self.rows + 1
        return Task.cont


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
    pass

class PandaWidget(ape.PandaWidget):
    pass




#endregion real main
if __name__ == '__main__':
    #ape.start(WindowTitle, EngineClass, terrainGenDemo, AppClass, MainWindowClass, PandaWidget, True, SupportsRenderPipeline)
    ape.start(WindowTitle, EngineClass, Grid, AppClass, MainWindowClass, PandaWidget, True, SupportsRenderPipeline)
