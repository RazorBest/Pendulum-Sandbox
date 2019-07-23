import wx
import updatable
from Queue import Queue
from math import sin, cos

class GraphableData():
    def __init__(self, values=[], colour=None, visible=True):
        self.__values = values
        self.__colour = colour
        self.__visible = visible
        self.__iterator = 0

    @property
    def values(self):
        return self.__values

    @values.setter
    def values(self, values):
        self.__values = values

    @property
    def colour(self):
        return self.__colour

    @colour.setter
    def colour(self, colour):
        self.__colour = colour

    @property
    def visible(self):
        return self.__visible

    @visible.setter
    def visible(self, visible):
        self.__visible = visible

    @property
    def active(self):
        return self.__active

    @active.setter
    def active(self, active):
        self.__active = active

    @property
    def iterator(self):
        return self.__iterator

    @iterator.setter
    def iterator(self, iterator):
        self.__iterator = iterator

class EnergyExtension(updatable.Updatable):
    def __init__(self, pendulum, ticksPerUpdate=1, totalColourId=wx.BLACK, kineticColourId=wx.RED, potentialColourId=wx.BLUE):
        updatable.Updatable.__init__(self, ticksPerUpdate)

        self.pendulum = pendulum
        objects = self.pendulum.GetVariableObjects()
        self.angles = objects['angles']
        self.velocities = objects['velocities']
        self.masses = objects['masses']
        self.lengths = objects['lengths']
        self.g = objects['g']

        self.totalEnergyColour = wx.Colour(totalColourId)
        self.kineticEnergyColour = wx.Colour(kineticColourId)
        self.potentialEnergyColour = wx.Colour(potentialColourId)

        self.data = {"total":GraphableData(values=[0], colour=self.totalEnergyColour), 
                    "kinetic":GraphableData(values=[0], colour=self.kineticEnergyColour), 
                    "potential":GraphableData(values=[0], colour=self.potentialEnergyColour)
                    }
    
    def GetPotentialEnergy(self):
        energy = 0
        n = len(self.masses)
        # Suppose the pivot has coordinates (0, 0)
        y = 0
        total_length = 0
        for i in range(n):
            y += cos(self.angles[i]) * self.lengths[i]
            total_length += self.lengths[i]
            energy += self.masses[i] * self.g * (total_length - y)

        return energy

    def GetKineticEnergy(self):
        energy = 0
        n = len(self.masses)
        vx = 0
        vy = 0
        for i in range(n):
            vx += self.lengths[i] * self.velocities[i] * cos(self.angles[i])
            vy += self.lengths[i] * self.velocities[i] * sin(self.angles[i])
            energy += self.masses[i] * (vx * vx + vy * vy) * 1. / 2

        return energy

    # Overload from Updatable class
    def UpdateData(self):
        pass

    def AddValue(self, key, value):
        self.data[key].values.append(value)

    def SetColours(self, total=None, kinetic=None, potential=None):
        if total != None:
            self.data['total'].colour = total
        if kinetic != None:
            self.data['kinetic'].colour = kinetic
        if potential != None:
            self.data['potential'].colour = potential

if __name__ == '__main__':
    from pendulum import PendulumBase

    pend = PendulumBase(1, 1, 0.0001)
    pend.AddBob(1, angle=3, mass=1, length=100)
    pend.AddBob(2, angle=3.1415, mass=1, length=100)
    pend.AddBob(3, length=100, angle=3.1415, mass=1)
    ee = EnergyExtension(pend)
    variables = pend.GetVariableObjects()

    mini = ee.GetPotentialEnergy() + ee.GetKineticEnergy()
    maxi = mini
    
    print "Init total: " + str(mini)

    for i in range(0, 30000):
        pend.Tick()
        total = ee.GetPotentialEnergy() + ee.GetKineticEnergy()
        mini = min(mini, total)
        maxi = max(maxi, total)

    print "Current total: " + str(ee.GetPotentialEnergy() + ee.GetKineticEnergy())
    print "Min: " + str(mini)
    print "Max: " + str(maxi)
    print variables
