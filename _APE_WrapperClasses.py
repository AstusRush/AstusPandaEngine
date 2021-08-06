# Do not import this file! Instead use `Classes` from AstusPandaEngine!
# While the normal objects from Panda3D are fully supported I don't like the API. This file contains my own API to work with Panda3D.
# The intention is not:
#   - to make a wrapper for every class, method or function from panda3d
#   - to replace the panda3d import
#
# The intention is:
#   - to provide the basic functionality of Panda3d
#   - to provide some QoL features
#   - to automate the setup while minimizing the loss of control that inevitably comes with this
#
# In addition the classes are fully compatible with hte tobsprRenderPipeline but do not require it to work.
#       This makes it easy to make games that support both.
# 
import panda3d as p3d
import panda3d.core as p3dc

from AGeLib import App
import sys

global rpcore
rpcore = None

#region shortcut functions
def engine():
    return App().engine

def base():
    return App().base
    
def render():
    return App().base.render
    
def loader():
    return App().base.loader

def window():
    return App().MainWindow

def lightManager():
    return App().lightManager

def pipelineActive():
    return App().RenderPipelineActive
#endregion shortcut functions

def _PipelineImport():
    sys.path.insert(0, "../tobsprRenderPipeline")
    sys.path.insert(0, "tobsprRenderPipeline")
    # Import render pipeline classes
    global rpcore
    from tobsprRenderPipeline import rpcore


#region Light

class _lightManager():
    lights = []
    def __init__(self):
        pass

    def addPointLight(self,pos=(0,0,0),col=(1,1,1)):
        return PointLight(pos,col)

    def purgeLights(self):
        if pipelineActive():
            for i in self.lights:
                try:
                    base().render_pipeline.remove_light(i.light)
                except:
                    pass
        else:
            render().clearLight()
        for i in self.lights:
            try:
                if not pipelineActive(): del i.node
                del i
            except:
                pass
        self.lights = []

    def darkness(self, darkness = True):
        pass #TODO: Turn all lights off

class PointLight():
    def __init__(self,pos=(0,0,0),col=(1,1,1)):
        if type(pos) != tuple or len(pos) != 3:
            raise TypeError("pos must be a tuple with length 3. {} is not supported with length {}.".format(type(col),len(pos)))
        elif type(col) != tuple or len(col) != 3:
            raise TypeError("col must be a tuple with length 3. {} is not supported with length {}.".format(type(col),len(col)))
        if pipelineActive():
            self.light = rpcore.PointLight()
            self.light.color = col[:3]
            self.light.casts_shadows = True
            self.light.pos = pos
            self.light.energy = 10000.0
            self.light.radius = 100
            self.light.shadow_map_resolution = 512
            self.light.near_plane = 0.2
            self.light.ies_profile = base().render_pipeline.load_ies_profile("x_arrow.ies")
            #self.light.set_color_from_temperature(1000.0)
            base().render_pipeline.add_light(self.light)
        else:
            self.light = p3dc.PointLight("plight")
            self.light.setColor(col+(5,))
            self.node = render().attachNewNode(self.light)
            self.node.setPos(pos)
            render().set_light(self.node)
        lightManager().lights.append(self) #TODO: Remove when this is deleted

#endregion Light