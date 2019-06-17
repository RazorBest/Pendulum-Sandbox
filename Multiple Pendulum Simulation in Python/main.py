"""
    This is a simulation of an n-link pendulum
"""
from __future__ import division
import os
import time
import threading
import wx
import wx.lib.agw.pycollapsiblepane as wxcp
import wx.lib.newevent
import wx.lib.scrolledpanel as wxsp
import explorer
import widgets
import extensions
from pendulum import Pendulum, CollisionState
from math import sqrt, atan2

class BufferedWindow(wx.Window):
    """A class used for drawing a BufferdWindow
    It prevents flickering.
    """
    def __init__(self, *args, **kwargs):
        kwargs['style'] = kwargs.setdefault('style', wx.NO_FULL_REPAINT_ON_RESIZE | wx.NO_FULL_REPAINT_ON_RESIZE)
        wx.Window.__init__(self, *args, **kwargs)

        # Setting up the event handlers
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSizeBufferedWindow)

    # This funtion is for subclasses
    def Draw(self, dc):
        pass

    def UpdateDrawing(self):
        dc = wx.MemoryDC()
        dc.SelectObject(self._Buffer)
        self.Draw(dc)
        del dc
        wx.CallAfter(self.Paint)

    def OnSizeBufferedWindow(self, e=None):
        size = self.GetClientSize()
        self._Buffer = wx.Bitmap(size)
        self.UpdateDrawing()
        if e != None:
            e.Skip()

    def OnPaint(self, e=None):
        self.Draw(wx.BufferedPaintDC(self, self._Buffer))

    # Does the same thing as OnPaint but is called by the client, not from a PaintEvent handler
    def Paint(self):
        self.Draw(wx.BufferedDC(wx.ClientDC(self), self._Buffer))

class SimulationWindow(BufferedWindow):
    main_thread = None

    #Giving each state a unique bit
    MOVING_STATE = 1
    ENTERED_STATE = 2
    CREATION_STATE = 4
    DRAG_STATE = 8
    HOVER_STATE = 16
    STARTED_STATE = 32

    def __init__(self, *args, **kwargs):
        self.ticksPerSecond = 1500

        kwargs['name'] = 'simulationWindow'
        BufferedWindow.__init__(self, *args, **kwargs)

        self.running = False
        self.SetBackgroundColour(wx.WHITE)

        self.pendulumHandler = PendulumHandler()
        self.pendulumCreator = PendulumCreator(self.pendulumHandler)
        
        explorerPanel = explorer.UserResizableWindow(self, self.pendulumHandler, size=(190, 0), style=wx.BORDER_SIMPLE)

        frictionGlider = widgets.FrictionGlider(self, eventHandler=self.pendulumHandler, size=(100, 50))

        self.energyDisplay = widgets.EnergyDisplay(self, self.ticksPerSecond, size=(0, 200), style=wx.BORDER_SIMPLE)

        frictionGliderSizer = wx.BoxSizer(wx.HORIZONTAL)
        #Add a very high proportion compared to the frictionGlider so it will aligned to the right
        frictionGliderSizer.AddStretchSpacer(10000)
        frictionGliderSizer.Add(frictionGlider, 1, flag=wx.ALIGN_RIGHT)

        widgetSizer = wx.BoxSizer(wx.VERTICAL)
        widgetSizer.Add(frictionGliderSizer, 1)
        widgetSizer.AddStretchSpacer(10000)
        widgetSizer.Add(self.energyDisplay, 1, wx.EXPAND|wx.ALIGN_BOTTOM)

        windowSizer = wx.BoxSizer(wx.HORIZONTAL)
        windowSizer.Add(explorerPanel, 0, wx.EXPAND)
        windowSizer.Add(widgetSizer)
        windowSizer.Layout()
        self.SetSizer(windowSizer)

        self.energyDisplay.SetPosition((300, 300))

        self.pendulumHandler.SetPendulumEventHandler(explorerPanel.GetChildren()[0])

        self.Bind(wx.EVT_MOTION, self.OnMouseMove)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_ENTER_WINDOW, self.OnEnterWindow)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeaveWindow)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

        self.clicked = False
        self.originX = 200
        self.originY = 200
        self.scale = 1
        self.lastMouseX = 0
        self.lastMouseY = 0

        self.state = 0

        self.dragState = CollisionState()
        self.hoverState = CollisionState()
        self.pause = True

        self.gridSpace = 100
        self.grid = Grid(self, space=self.gridSpace, minScaleLim=0.2, maxScaleLim=6, colourCode=(200, 200, 200))
        self.Bind(wx.EVT_MOUSEWHEEL, self.grid.OnMouseWheel)

        self.timer = wx.Timer(self)

        self.Bind(wx.EVT_TIMER, self.OnTimer, self.timer)
        self.Bind(wx.EVT_SIZE, self.OnSize)

        wx.CallLater(1000, self.StartThread)

        print "SimulationWindow initiated"

    def StartThread(self):
        self.timer.Start(1000. / 200)

        self.running = True
        self.main_thread = threading.Thread(target=self.run)
        self.main_thread.daemon = True
        self.main_thread.start()

    def StopThread(self):
        self.timer.Stop()

        if self.running:
            self.running = False
            self.main_thread.join()

    def run(self):
        print "Thread started"

        lastTime = time.clock()
        ticksPerSecond = self.ticksPerSecond
        tickInterval = 1. / ticksPerSecond

        while self.running:
            currentTime = time.clock()

            while currentTime - lastTime >= tickInterval:
                if self.pause != True:
                    self.Tick()
                lastTime += tickInterval

    def Tick(self):
        self.pendulumHandler.Tick()
        self.energyDisplay.Tick()

    def OnTimer(self, e):
        self.UpdateDrawing()

    def Draw(self, dc):
        dc.Clear()

        dc.SetDeviceOrigin(self.originX, self.originY)

        self.grid.Draw(dc)

        #Drawing the origin
        dc.DrawCircle(0, 0, 3)
        dc.DrawLine(-15, 0, 15, 0)
        dc.DrawLine(0, -15, 0, 15)

        dc.SetUserScale(self.scale, self.scale)

        #Draws a light gray circle for the space in which will be the future pivot
        if not (self.state & (self.MOVING_STATE | self.STARTED_STATE)) and self.hoverState.id == 0 and self.state & self.ENTERED_STATE:
            dc.SetPen(wx.Pen(wx.Colour(175, 175, 175)))
            dc.SetBrush(wx.Brush(wx.Colour(175, 175, 175)))
            dc.DrawCircle(self.TranslateCoord(self.lastMouseX, self.lastMouseY), 10)

        self.pendulumHandler.Draw(dc)
        if self.state & self.CREATION_STATE:
            self.pendulumCreator.Draw(dc)

    def TranslateCoord(self, x, y):
        return (x - self.originX) / self.scale, (y- self.originY) / self.scale

    def ChangeCursor(self, stockCursor):
        self.SetCursor(wx.Cursor(stockCursor))
        if stockCursor == wx.CURSOR_ARROW:
            self.state &= ~self.MOVING_STATE
        elif stockCursor == wx.CURSOR_SIZING:
            self.state |= self.MOVING_STATE

    def SetPause(self, pause):
        self.pause = pause
        if pause == False:
            self.state |= self.STARTED_STATE

    def Reload(self):
        self.pause = True
        self.state &= ~self.STARTED_STATE
        self.pendulumHandler.ReleaseStack()
        self.pendulumHandler.SendParameters()

    def OnSize(self, e=None):
        self.grid.SetSpace(self.gridSpace * self.scale)
        width, height = self.GetSize()
        self.grid.SetWidth(width + 200)
        self.grid.SetHeight(height + 200)
        self.grid.SetX(-self.originX)
        self.grid.SetY(-self.originY)
        if e != None:
            e.Skip()

    def OnEnterWindow(self, e):
        self.state |= self.ENTERED_STATE
        #self.SetFocus()

    def OnLeaveWindow(self, e):
        self.state &= ~self.ENTERED_STATE
        if self.state & self.CREATION_STATE:
            self.FinishCreation()

    def OnMouseMove(self, e):
        x, y = e.x, e.y

        dx = x - self.lastMouseX
        dy = y - self.lastMouseY
        self.lastMouseX = x
        self.lastMouseY = y

        if not e.LeftIsDown():
            self.hoverState = self.pendulumHandler.PendulumCollision(*self.TranslateCoord(x, y))
            return

        if self.state & self.MOVING_STATE:
            self.originX += dx
            self.originY += dy

            self.grid.SetX(-self.originX)
            self.grid.SetY(-self.originY)
            return

        if self.dragState.id != 0:
            pendulumId = self.dragState.id
            self.pendulumHandler.MovePendulum(pendulumId, dx / self.scale, dy / self.scale)

        if self.state & self.STARTED_STATE:
            return

        if self.state & self.CREATION_STATE:
            self.pendulumCreator.SetXY(*self.TranslateCoord(x, y))
            return

    def OnLeftDown(self, e):
        x, y = self.TranslateCoord(e.x, e.y)

        # If the cursor is in the moving state, 
        #   meaning the user can only move through the working space and he can't create pendulums or interact with them
        if self.state & self.MOVING_STATE:
            return

        self.hoverState = self.pendulumHandler.PendulumCollision(x, y)
        self.dragState = self.hoverState
        pendulumId = self.hoverState.id

        # If the cursor is over any pendulum 
        if pendulumId != 0:
            if not self.pendulumHandler.IsSelected(pendulumId):
                self.pendulumHandler.SelectPendulum(pendulumId, True)
                return

            if self.hoverState.lastBob and not (self.state & self.STARTED_STATE):
                self.hoverState = CollisionState()
                self.StartCreation(pendulumId, x, y)
                self.dragState = CollisionState()
            else:
                self.pendulumHandler.SelectPendulum(pendulumId, True)
        # If the cursor is not over any pendulum it means it can be created a new pendulum
        # You can't create a pendulum if the simulation has started (that's what the condition is checking)
        elif not (self.state & self.STARTED_STATE):
            #extend a pendulum with a bob with its pivot at coorinates (x, y)
            pendulumId = self.pendulumHandler.AddPendulum(x, y, 1. / self.ticksPerSecond)
            self.hoverState = CollisionState()
            self.dragState = CollisionState()
            self.StartCreation(pendulumId, x, y)

    def OnLeftUp(self, e):
        if self.state & self.CREATION_STATE:
            x, y = self.TranslateCoord(e.GetX(), e.GetY())
            self.FinishCreation()
            self.hoverState = self.pendulumHandler.PendulumCollision(*self.TranslateCoord(x, y))

    def OnMouseWheel(self, e):
        mag = self.scale * e.GetWheelRotation() / e.GetWheelDelta() / 25.
        mx = e.GetX()
        my = e.GetY()

        if self.scale + mag > 0.2 and self.scale + mag < 6:
            self.originX -= (mx - self.originX) * mag / self.scale
            self.originY -= (my - self.originY) * mag / self.scale
            self.scale += mag

    def GetPendulumHandler(self):
        return self.pendulumHandler

    def SetExtension(self, extension):
        self.energyDisplay.extension = extension

    def AddPendulum(self, x=300, y=200):
        x, y = self.TranslateCoord(x, y)

        return self.pendulumHandler.AddPendulum(x, y, 1. / self.ticksPerSecond)

    def StartCreation(self, pendulumId, x=0, y=0):
        self.pendulumCreator.SetPendulumId(pendulumId)
        self.pendulumCreator.SetXY(x, y)
        self.state |= self.CREATION_STATE

    def FinishCreation(self):
        self.pendulumCreator.Add()
        self.state &= ~self.CREATION_STATE
        pendulumId = self.pendulumCreator.GetPendulumId()
        self.pendulumHandler.SelectPendulum(pendulumId)

    def GetCameraOrigin(self):
        return (self.originX, self.originY)

    def IsPaused(self):
        return self.pause

    def IsStarted(self):
        return self.state & self.STARTED_STATE

    def OnClose(self, e):
        self.StopThread()
        print 'closing simulationWindow'

class Grid():
    def __init__(self, parentWindow, x=0, y=0, width=0, height=0, space=100, minScaleLim=0.2, maxScaleLim=6, colourCode=wx.BLACK):
        self.parentWindow = parentWindow
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.colourCode = colourCode
        self.space = space
        self.gridSpaceStart = space
        self.gridSpace = space
        self.minScaleLim = minScaleLim
        self.maxScaleLim = maxScaleLim
        self.scale = 1
        self.mouseScale = 1

    def SetX(self, x):
        self.x = x

    def SetY(self, y):
        self.y = y

    def SetWidth(self, width):
        self.width = width

    def SetHeight(self, height):
        self.height = height

    def SetSpace(self, space):
        self.space = space

    def SetScale(self, scale):
        self.scale = scale

    def SetColour(self, colour):
        self.colour = colour
        
    def OnMouseWheel(self, e):
        mag = self.mouseScale * e.GetWheelRotation() / e.GetWheelDelta() / 25.
        mx = e.GetX()
        my = e.GetY()

        if self.mouseScale + mag > self.minScaleLim and self.mouseScale + mag < self.maxScaleLim:
            self.mouseScale += mag

            if self.gridSpace * self.mouseScale < 50:
                self.gridSpace = 100 / self. mouseScale

            if self.gridSpace * self.mouseScale > 100:
                self.gridSpace = 50 / self.mouseScale

            self.SetSpace(self.gridSpace * self.mouseScale)

            originX, originY = self.parentWindow.GetCameraOrigin()
            self.SetX(-originX)
            self.SetY(-originY)

        e.Skip()

    def Draw(self, dc):
        """Draws a set of parallel, horizontal and vertical lines, inside a rectangle determined by the x, y, w, h variables
            (x,y) is the upper-left corner of the rectangle and w, h are it dimensions"""
        dc.SetPen(wx.Pen(wx.Colour(self.colourCode)))
        dc.SetBrush(wx.Brush(wx.Colour(self.colourCode)))

        w = self.width
        h = self.height
        x = self.x
        y = self.y

        #Draws the horizontal lines
        l1 = y - y % self.space
        while l1 <= y + h:
            dc.DrawLine(x, l1, x + w, l1)
            l1 += self.space

        #Draws the vertical lines
        c1 = x - x % self.space
        while c1 <= x + w:
            dc.DrawLine(c1, y, c1, y + h)
            c1 += self.space

        #Draws the Ox and Oy lines
        dc.SetPen(wx.Pen(wx.Colour(wx.BLACK)))
        dc.SetBrush(wx.Brush(wx.Colour(wx.BLACK)))
        dc.DrawLine(x, 0, x + w, 0)
        dc.DrawLine(0, y, 0, y + h)

        #dc.DrawLine(0, -150, 100 * self.scale, -150)

        #Draws the numbers along the x axis
        """c1 = x - x % self.space #c1 is the x coordonate of the starting point
        number = c1 / self.space
        print number
        while c1 <= x + w:
            number = round(number, 2)
            dc.DrawText("{0:.2f}".format(number), c1, 0)
            c1 += self.space
            number += self.gridSpaceStart / self.space""" 

"""class ZoomHandler(wx.EvtHandler):
    def __init__(self):
        wx.EvtHandler(self)
"""
        

class PendulumCreator():
    def __init__(self, pendulumHandler, pivotX=None, pivotY=None, pendulumId=0, x=0, y=0):
        self.pendulumHandler = pendulumHandler
        self.penulumId=pendulumId
        self.pivotX = pivotX
        self.pivotY = pivotY
        self.x = x
        self.y = y
        self.start = False

    def SetPendulumId(self, pendulumId):
        self.pendulumId = pendulumId
        self.pivotX, self.pivotY = self.pendulumHandler.GetBobPos(pendulumId)
        self.start = False

    def GetPendulumId(self):
        return self.pendulumId

    def SetPivot(self, pivotX, pivotY):
        self.pivotX = pivotX
        self.pivotY = pivotY

    def CheckIfCanStart(self):
        y = (self.x - self.pivotX)
        x = (self.y - self.pivotY)
        length = sqrt(x**2 + y**2)
        if length > 30:
            self.start = True

    def SetXY(self, x, y):
        self.x = x
        self.y = y
        self.CheckIfCanStart()

    def SetX(self, x):
        self.x = x
        self.CheckIfCanStart()

    def SetY(self, y):
        self.y = y
        self.CheckIfCanStart()

    def Add(self):
        if not self.start:
            return

        y = (self.x - self.pivotX)
        x = (self.y - self.pivotY)
        length = sqrt(x**2 + y**2)
        angle = atan2(y, x)
        length = round(length, 3)
        angle = round(angle, 3)
        values = {'l':length, 'a':angle}

        #Send the event the the PendulumHandler
        pendulumEvent = explorer.BobCreationStartEvent(
            pendulumId=self.pendulumId,
            values=values)
        wx.PostEvent(self.pendulumHandler, pendulumEvent)

    def Draw(self, dc):
        if not self.start:
            return

        dc.SetBrush(wx.Brush(wx.Colour(wx.BLACK)))
        dc.SetPen(wx.Pen(wx.Colour(wx.BLACK), style=wx.PENSTYLE_LONG_DASH))
        dc.DrawLine(self.pivotX, self.pivotY, self.x, self.y)

class DataHolder():
    def __init__(self, val=None):
        self.val = val

class PendulumHandler(wx.EvtHandler):
    """This class has a list of all the pendulums
    You can add/delete a pendulum
        and you can call tick/draw method on all pendulums
    """

    defaultVariableList = {'m':10, 'l':100, 'a':0, 'v':0}

    def __init__(self):
        wx.EvtHandler.__init__(self)

        self.pendulumDict = {}
        self.extensionDict = {}
        self.futurePendulumDict = {}
        self.futureBobDict = {}
        self.variableList = {}
        self.pendulumLinker = {}
        self.bobLinker = {}
        self.pendulumId = 0
        self.bobId = 0
        self.timeInterval = 1000

        self.pendulumEventHandler = None
        self.simulationWindow = wx.FindWindowByName('simulationWindow')

        self.Bind(explorer.EVT_PENDULUM_CREATION_START, self.OnPendulumCreation)
        self.Bind(explorer.EVT_BOB_CREATION_START, self.OnBobCreation)
        self.Bind(widgets.EVT_FRICTION_UPDATE, self.OnFrictionUpdate)

    def OnPendulumCreation(self, e):
        pendulumId = self.simulationWindow.AddPendulum()

    def OnBobCreation(self, e):
        if e.values == None:
            e.values = {}
        self.CompleteValueDict(e.values)
        bobId = self.AddBob(pendulumId=e.pendulumId, valueDict=e.values)
    
    def OnFrictionUpdate(self, e):
        Pendulum.frictionCoefficient = e.value

    def CompleteValueDict(self, valueDict):
        for variable, value in self.defaultVariableList.iteritems():
            if not (variable in valueDict):
                valueDict[variable] = value

    def AddPendulum(self, x, y, timeInterval=None):
        if timeInterval == None:
            timeInterval = self.timeInterval
        self.pendulumId += 1
        pendulum = Pendulum(x, y, timeInterval)
        ee = extensions.EnergyExtension(pendulum)
        self.extensionDict[self.pendulumId] = ee
        if not self.simulationWindow.IsStarted():
            self.pendulumDict[self.pendulumId] = pendulum
            self.simulationWindow.SetExtension(ee)
        else:
            self.futurePendulumDict[self.pendulumId] = pendulum
        self.variableList[self.pendulumId] = dict()

        #Send the event to the Explorer
        pendulumEvent = explorer.PendulumCreationReadyEvent(pendulumId=self.pendulumId)
        wx.PostEvent(self.pendulumEventHandler, pendulumEvent)

        return self.pendulumId

    def AddBob(self, pendulumId=None, obj=None, valueDict=None):
        if pendulumId == None and obj == None:
            return 0

        self.bobId += 1

        external = True
        if pendulumId == None:
            pendulumId = self.pendulumLinker[obj]
            external = False

        if not self.simulationWindow.IsStarted():
            self.CreateBob(pendulumId, self.bobId)
        elif self.pendulumDict.get(pendulumId) != None:
            self.futureBobDict.setdefault(pendulumId, [])
            self.futureBobDict[pendulumId].append(self.bobId)
        else:
            self.futurePendulumDict[pendulumId].AddBob(self.bobId)
        self.variableList[pendulumId][self.bobId] = self.CreateDataDict(self.defaultVariableList)

        if obj == None:
            obj = self.FindObjFromPendumulId(pendulumId)
        
        #Send the event to the linked object(PendulumEditor)
        pendulumEvent = explorer.BobCreationReadyEvent(bobId=self.bobId, valueDict=valueDict)
        wx.PostEvent(obj, pendulumEvent)

        if not self.simulationWindow.IsStarted():
            self.SetParameters(pendulumId, self.bobId, valueDict, send=True)

        return self.bobId

    def CreateBob(self, pendulumId, bobId):
        self.pendulumDict[pendulumId].AddBob(bobId)

    def RemoveBob(self, pendulumId, bobId):
        print "pendulumId: " + str(pendulumId)
        print self.futureBobDict
        if self.pendulumDict.get(pendulumId) != None:
            if pendulumId in self.futureBobDict and bobId in self.futureBobDict[pendulumId]:
                self.futureBobDict[pendulumId].remove(bobId)
            else:
                self.pendulumDict[pendulumId].RemoveBob(bobId)
        else:
            self.futurePendulumDict[pendulumId].RemoveBob(bobId)
            
        del self.variableList[pendulumId][bobId]

    def RemovePendulum(self, pendulumId):
        if self.pendulumDict.get(pendulumId) != None:
            del self.pendulumDict[pendulumId]
            if pendulumId in self.futureBobDict:
                del self.futureBobDict[pendulumId]
        else:
            del self.futurePendulumDict[pendulumId]

        del self.variableList[pendulumId]

    def CreateDataDict(self, dct):
        new_dict = dict()
        for key, value in dct.iteritems():
            new_dict[key] = DataHolder(value)
        return new_dict

    def SetTimeInterval(self, timeInterval):
        """You can call this funtion before
            adding a sequence pendulums with the same timeInterval
        """
        self.timeInterval = timeInterval

    def LinkVariable(self, obj, pendulumId, bobId, name):
        self.bobLinker[obj] = self.variableList[pendulumId][bobId][name]

    def UnlinkVariable(self, obj):
        del self.bobLinker[obj]

    def LinkPendulum(self, obj, pendulumId):
        self.pendulumLinker[obj] = pendulumId

    def SetParameter(self, pendulumId, bobId, name, value):
        self.variableList[pendulumId][bobId][name].val = value

    def SetParameters(self, pendulumId, bobId, valueDict, send=False):
        for name, val in valueDict.items():
            self.variableList[pendulumId][bobId][name].val = val

        self.RefreshLinkedVariables()

        if send:
            self.SendParameters()

    def RefreshLinkedVariables(self):
        for obj, holder in self.bobLinker.items():
            obj.SetParameter(holder.val)

    def FindObjFromPendumulId(self, pendulumId):
        for obj, thisId in self.pendulumLinker.items():
            if pendulumId == thisId:
                return obj

    def SetParameter(self, obj, value):
        self.bobLinker[obj].val = value

    def SendParameters(self):
        for pendulumId, pendulum in self.pendulumDict.items():
            for bobId, parameters in self.variableList[pendulumId].items():
                pendulum.SetBob(
                    bobId,
                    parameters['m'].val,
                    parameters['l'].val,
                    parameters['a'].val,
                    parameters['v'].val)

    def ReleaseStack(self):
        for pendulumId, pendulum in self.futurePendulumDict.items():
            self.pendulumDict[pendulumId] = pendulum
        self.futurePendulumDict = {}
        for pendulumId, bobList in self.futureBobDict.items():
            for bobId in bobList:
                self.CreateBob(pendulumId, bobId)
        self.futureBobDict = {}

    def PendulumCollision(self, mx, my):
        for pendulumId, pendulum in self.pendulumDict.items():
            state = pendulum.PendulumCollision(mx, my)
            if state.pivot or state.bobIndex or state.rod:
                state.id = pendulumId
                return state
            #if ans.count(0) < 3:
            #   return (pendulumId,) + ans

        # Return the default state
        return CollisionState()

    def MovePendulum(self, pendulumId, dx, dy):
        pend = self.pendulumDict[pendulumId]
        pend.SetX(pend.GetX() + dx)
        pend.SetY(pend.GetY() + dy)

    def SelectPendulum(self, pendulumId, selected=True):
        for pendulum in self.pendulumDict.values():
            pendulum.SetSelected(False)
        self.pendulumDict[pendulumId].SetSelected(selected)
        if selected == True:
            self.simulationWindow.SetExtension(self.extensionDict[pendulumId])

    def IsSelected(self, pendulumId):
        return self.pendulumDict[pendulumId].IsSelected()

    def GetBobPos(self, pendulumId, bobId=None):
        """Get the cartesian coordinates of the respective bob
        """
        return self.pendulumDict[pendulumId].GetPos(bobId)

    def Tick(self):
        for pendulum in self.pendulumDict.values():
            pendulum.Tick()

    def Draw(self, dc):
        for pendulum in self.pendulumDict.values():
            pendulum.Draw(dc)

    def SetPendulumEventHandler(self, pendulumEventHandler):
        self.pendulumEventHandler = pendulumEventHandler

class MainFrame(wx.Frame):
    """Derive a new class from Frame"""
    def __init__(self, parent, title):
        width = 800
        height = 600

        wx.Frame.__init__(self, parent, title=title, size=(width, height),
            style=wx.DEFAULT_FRAME_STYLE ^ wx.CLIP_CHILDREN)

        #Creating the toolbar with its items
        toolbar = self.CreateToolBar()
        self.selectionTool = toolbar.AddRadioTool(wx.ID_ANY, 'Selection', wx.Bitmap('icons/selection.png'))
        self.moveTool = toolbar.AddRadioTool(wx.ID_ANY, 'Move', wx.Bitmap('icons/move.png'))
        toolbar.AddSeparator()
        self.playTool = toolbar.AddRadioTool(wx.ID_ANY, 'Play', wx.Bitmap('icons/play.png'))
        self.pauseTool = toolbar.AddRadioTool(wx.ID_ANY, 'Pause', wx.Bitmap('icons/pause.png'))
        toolbar.ToggleTool(self.pauseTool.GetId(), True)
        self.reloadTool = toolbar.AddTool(wx.ID_ANY, 'Reload', wx.Bitmap('icons/reload.png'))
        toolbar.Realize()

        # Set events
        self.Bind(wx.EVT_TOOL, self.OnChangeCursor, self.selectionTool)
        self.Bind(wx.EVT_TOOL, self.OnChangeCursor, self.moveTool)
        self.Bind(wx.EVT_TOOL, self.OnTogglePlay, self.playTool)
        self.Bind(wx.EVT_TOOL, self.OnTogglePlay, self.pauseTool)
        self.Bind(wx.EVT_TOOL, self.OnReload, self.reloadTool)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

        self.simulationWindow = SimulationWindow(self, size=(width, 0))

        self.Centre()
        self.Show(True)

    def OnChangeCursor(self, e):
        id = e.GetId()
        if id == self.selectionTool.GetId():
            self.simulationWindow.ChangeCursor(wx.CURSOR_ARROW)
        elif id == self.moveTool.GetId():
            self.simulationWindow.ChangeCursor(wx.CURSOR_SIZING)

    def OnTogglePlay(self, e):
        id = e.GetId()
        if id == self.playTool.GetId():
            self.simulationWindow.SetPause(False)
        elif id == self.pauseTool.GetId():
            self.simulationWindow.SetPause(True)

    def OnReload(self, e):
        self.GetToolBar().ToggleTool(self.pauseTool.GetId(), True)
        self.simulationWindow.Reload()

    def OnClose(self, e):
        with wx.MessageDialog(self, "Are you sure you want to quit?", caption="Quit?", style=wx.YES_NO|wx.CANCEL|wx.CANCEL_DEFAULT|wx.ICON_QUESTION) as dialog:
            if dialog.ShowModal() == wx.ID_YES:
                self.simulationWindow.Close(True)
                e.Skip()

def main():
    app = wx.App(False)
    frame = MainFrame(None, title='Pendulum Sandbox')

    frame.Show(True)
    app.MainLoop()


if __name__ == "__main__":
    main()
