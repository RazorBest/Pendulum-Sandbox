import time

class Updatable(object):
    """This class handles an object that can be updated repeatedly within a given time interval(updateInterval)
        or can be updated after a given tick count (ticksPerUpdate)"""
    def __init__(self, ticksPerUpdate=None, updateInterval=None):
        assert(ticksPerUpdate != None or updateInterval != None), "__init__() function of LiveObject needs one keyword argument" 

        self.__ticksPerUpdate = ticksPerUpdate
        self.ticks = 0

        self.__updateInterval = updateInterval
        self.lastUpdated = None

        self.__pause = False

    def UpdateData(self):
        """This function is be implemented by subclasses"""
        pass

    def Tick(self):
        if self.__pause:
            return

        if self.__ticksPerUpdate != None:

            self.ticks += 1
            if self.ticks >= self.__ticksPerUpdate:
                self.ticks = 0
                self.UpdateData()
        else:
            if self.lastUpdated == None:
                self.lastUpdated = time.clock()

            currentTime = time.clock()
            while currentTime - self.lastUpdated >= self.__updateInterval:
                self.lastUpdated += self.__updateInterval
                self.UpdateData()

    @property
    def ticksPerUpdate(self):
        return self.__ticksPerUpdate
    
    @ticksPerUpdate.setter
    def ticksPerUpdate(self, ticksPerUpdate):
        self.__ticksPerUpdate = ticksPerUpdate
    
    @property
    def updateInterval(self):
        return self.__updateInterval

    @updateInterval.setter
    def updateInterval(self, updateInterval):
        if updateInterval > 0.001 and updateInterval < 1:
            self.__updateInterval = updateInterval

    @property
    def pause(self):
        return self.__pause

    @pause.setter
    def pause(self, pause):
        assert(isinstance(pause, bool)), "pause must be bool"
        if not pause and self.__updateInterval != None:
            self.lastUpdated = time.clock()
        self.__pause = pause