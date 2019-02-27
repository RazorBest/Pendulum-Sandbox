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
import re
from pendulum import Pendulum
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

    MOVING_STATE = 1
    ENTERED_STATE = 2
    CREATION_STATE = 4
    DRAG_STATE = 8
    HOVER_STATE = 16
    STARTED_STATE = 32

    def __init__(self, *args, **kwargs):
        self.ticksPerSecond = 500

        kwargs['name'] = 'simulationWindow'
        BufferedWindow.__init__(self, *args, **kwargs)

        self.running = False
        self.SetBackgroundColour(wx.WHITE)

        self.pendulumHandler = PendulumHandler()
        self.pendulumCreator = PendulumCreator(self.pendulumHandler)

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

        self.dragPendulum = (0,)
        self.hoverPendulum = (0,)
        self.pause = True

        self.gridSpace = 100
        self.grid = Grid(space=self.gridSpace, colourCode=(200, 200, 200))

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

    def OnTimer(self, e):
        self.UpdateDrawing()

    def Draw(self, dc):
        dc.Clear()

        dc.SetDeviceOrigin(self.originX, self.originY)

        self.grid.Draw(dc)

        #drawing the origin
        dc.DrawCircle(0, 0, 3)
        dc.DrawLine(-15, 0, 15, 0)
        dc.DrawLine(0, -15, 0, 15)

        dc.SetUserScale(self.scale, self.scale)

        if not (self.state & (self.MOVING_STATE | self.STARTED_STATE)) and self.hoverPendulum[0] == 0 and self.state & self.ENTERED_STATE:
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
        x, y = e.GetX(), e.GetY()

        dx = x - self.lastMouseX
        dy = y - self.lastMouseY
        self.lastMouseX = x
        self.lastMouseY = y

        if not e.LeftIsDown():
            self.hoverPendulum = self.pendulumHandler.PendulumCollision(*self.TranslateCoord(x, y))
            return

        if self.state & self.MOVING_STATE:
            self.originX += dx
            self.originY += dy

            self.grid.SetX(-self.originX)
            self.grid.SetY(-self.originY)
            return

        if self.dragPendulum[0] != 0:
            pendulumId = self.dragPendulum[0]
            self.pendulumHandler.MovePendulum(pendulumId, dx / self.scale, dy / self.scale)

        if self.state & self.STARTED_STATE:
            return

        if self.state & self.CREATION_STATE:
            self.pendulumCreator.SetXY(*self.TranslateCoord(x, y))
            return

    def OnLeftDown(self, e):
        x, y = self.TranslateCoord(e.GetX(), e.GetY())

        # If the cursor is in the moving state, 
        #   meaning the user can only move through the working space and he can't create pendulums or interact with them
        if self.state & self.MOVING_STATE:
            return

        self.hoverPendulum = self.pendulumHandler.PendulumCollision(x, y)
        pendulumId = self.hoverPendulum[0]

        # If the cursor is over any pendulum 
        if pendulumId != 0:
            if not self.pendulumHandler.IsSelected(pendulumId):
                self.pendulumHandler.SelectPendulum(pendulumId, True)
                self.dragPendulum = self.hoverPendulum
                return

            if self.hoverPendulum[3] != 0 and not (self.state & self.STARTED_STATE):
                self.hoverPendulum = (0,)
                self.StartCreation(pendulumId, x, y)
                self.dragPendulum = (0,)
            else:
                self.pendulumHandler.SelectPendulum(pendulumId, True)
                self.dragPendulum = self.hoverPendulum
        # If the cursor is not over any pendulum it means it can be created a new pendulum
        # You cant create a pendulum if the simulation has started (that's waht the condition is checking)
        elif not (self.state & self.STARTED_STATE):
            #extend a pendulum with a bob with its pivot at coorinates (x, y)
            pendulumId = self.pendulumHandler.AddPendulum(x, y, 1. / self.ticksPerSecond)
            wx.FindWindowByName('explorer').AddPendulum(pendulumId)  #This line should be handled in the future by the pendulumHandler
            self.hoverPendulum = (0,)
            self.dragPendulum = (0,)
            self.StartCreation(pendulumId, x, y)

    def OnLeftUp(self, e):
        if self.state & self.CREATION_STATE:
            x, y = self.TranslateCoord(e.GetX(), e.GetY())
            self.FinishCreation()
            self.hoverPendulum = self.pendulumHandler.PendulumCollision(*self.TranslateCoord(x, y))

    def OnMouseWheel(self, e):
        mag = self.scale * e.GetWheelRotation() / e.GetWheelDelta() / 25.
        mx = e.GetX()
        my = e.GetY()

        if self.scale + mag > 0.2 and self.scale + mag < 6:
            self.originX -= (mx - self.originX) * mag / self.scale
            self.originY -= (my - self.originY) * mag / self.scale
            self.scale += mag

            if self.gridSpace * self.scale < 50:
                self.gridSpace = 100 / self.scale

            if self.gridSpace * self.scale > 100:
                self.gridSpace = 50 / self.scale

            self.grid.SetSpace(self.gridSpace * self.scale)
            width, height = self.GetSize()
            self.grid.SetWidth(width + 200)
            self.grid.SetHeight(height + 200)

            self.grid.SetX(-self.originX)
            self.grid.SetY(-self.originY)

    def GetPendulumHandler(self):
        return self.pendulumHandler

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

    def IsPaused(self):
        return self.pause

    def IsStarted(self):
        return self.state & self.STARTED_STATE

    def OnClose(self, e):
        self.StopThread()
        print 'closing simulationWindow'

class Grid():
    def __init__(self, x=0, y=0, width=0, height=0, space=100, colourCode=wx.BLACK):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.colourCode = colourCode
        self.space = space
        self.scale = 1

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

    def Draw(self, dc):
        dc.SetPen(wx.Pen(wx.Colour(self.colourCode)))
        dc.SetBrush(wx.Brush(wx.Colour(self.colourCode)))

        w = self.width
        h = self.height
        x = self.x
        y = self.y

        l1 = y - y % self.space
        while l1 <= y + h:
            dc.DrawLine(x, l1, x + w, l1)
            l1 += self.space

        c1 = x - x % self.space
        while c1 <= x + w:
            dc.DrawLine(c1, y, c1, y + h)
            c1 += self.space

        dc.SetPen(wx.Pen(wx.Colour(wx.BLACK)))
        dc.SetBrush(wx.Brush(wx.Colour(wx.BLACK)))
        dc.DrawLine(x, 0, x + w, 0)
        dc.DrawLine(0, y, 0, y + h)

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

        bobId = self.pendulumHandler.AddBob(self.pendulumId)
        y = (self.x - self.pivotX)
        x = (self.y - self.pivotY)
        length = sqrt(x**2 + y**2)
        angle = atan2(y, x)
        length = round(length, 3)
        angle = round(angle, 3)
        values = {'l':length, 'a':angle}
        self.pendulumHandler.SetParameters(self.pendulumId, bobId, values, send=True)

    def Draw(self, dc):
        if not self.start:
            return

        dc.SetBrush(wx.Brush(wx.Colour(wx.BLACK)))
        dc.SetPen(wx.Pen(wx.Colour(wx.BLACK), style=wx.PENSTYLE_LONG_DASH))
        dc.DrawLine(self.pivotX, self.pivotY, self.x, self.y)

class DataHolder():
    def __init__(self, val=None):
        self.val = val

class PendulumHandler():
    """This class has a list of all the pendulums
    You can add/delete a pendulum
        and you can call tick/draw method on all pendulums
    """

    defaultVariableList = {'m':10, 'l':100, 'a':0, 'v':0}

    def __init__(self):
        self.pendulumDict = {}
        self.pendulumStack = {}
        self.bobStack = {}
        self.variableList = {}
        self.pendulumLinker = {}
        self.bobLinker = {}
        self.pendulumId = 0
        self.bobId = 0
        self.timeInterval = 1000

        self.simulationWindow = wx.FindWindowByName('simulationWindow')

    def AddPendulum(self, x, y, timeInterval=None):
        if timeInterval == None:
            timeInterval = self.timeInterval
        self.pendulumId += 1
        if not self.simulationWindow.IsStarted():
            self.pendulumDict[self.pendulumId] = Pendulum(x, y, timeInterval)
        else:
            self.pendulumStack[self.pendulumId] = Pendulum(x, y, timeInterval)
        self.variableList[self.pendulumId] = dict()

        return self.pendulumId

    def AddBob(self, pendulumId=None, obj=None):
        if pendulumId == None and obj == None:
            return 0

        self.bobId += 1

        external = True
        if pendulumId == None:
            pendulumId = self.pendulumLinker[obj]
            external = False

        if not self.simulationWindow.IsStarted():
            self.pendulumDict[pendulumId].AddBob(self.bobId)
        elif self.pendulumDict.get(pendulumId) != None:
            self.bobStack.setdefault(pendulumId, [])
            self.bobStack[pendulumId].append(self.bobId)
        else:
            self.pendulumStack[pendulumId].AddBob(self.bobId)
        self.variableList[pendulumId][self.bobId] = self.DataDict(self.defaultVariableList)

        if external:
            self.RefreshLinkedPendulum(pendulumId, self.bobId)

        return self.bobId

    def RemoveBob(self, pendulumId, bobId):
        if self.pendulumDict.get(pendulumId) != None:
            self.pendulumDict[pendulumId].RemoveBob(bobId)
        else:
            self.pendulumStack[pendulumId].RemoveBob(bobId)
        del self.variableList[pendulumId][bobId]

    def DataDict(self, dct):
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

    def RefreshLinkedPendulum(self, pendulumId, bobId):
        for obj, thisId in self.pendulumLinker.items():
            if pendulumId == thisId:
                obj.AddBob(bobId)
                return

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
        for pendulumId, pendulum in self.pendulumStack.items():
            self.pendulumDict[pendulumId] = pendulum
        self.pendulumStack = {}
        for pendulumId, bobList in self.bobStack.items():
            for bobId in bobList:
                self.pendulumDict[pendulumId].AddBob(bobId)
        self.bobStack = {}

    def PendulumCollision(self, mx, my):
        for pendulumId, pendulum in self.pendulumDict.items():
            ans = pendulum.PendulumCollision(mx, my)
            if ans.count(0) < 3:
                return (pendulumId,) + ans

        return (0,)

    def MovePendulum(self, pendulumId, dx, dy):
        pend = self.pendulumDict[pendulumId]
        pend.SetX(pend.GetX() + dx)
        pend.SetY(pend.GetY() + dy)

    def SelectPendulum(self, pendulumId, selected=True):
        for pendulum in self.pendulumDict.values():
            pendulum.SetSelected(False)
        self.pendulumDict[pendulumId].SetSelected(selected)


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


class NumberValidator(wx.Validator):
    def __init__(self, *args, **kwargs):
        self.min_val = None
        self.max_val = None

        if 'min_val' in kwargs:
            self.min_val = kwargs['min_val']
            del kwargs['min_val']
        if 'max_val' in kwargs:
            self.max_val = kwargs['max_val']
            del kwargs['max_val']
        
        wx.Validator.__init__(self, *args, **kwargs)

        self.lastText = None
        

    def SetMinMax(self, min_val=None, max_val=None):
        if min_val != None:
            self.min_val = min_val
        if max_val != None:
            self.max_val = max_val

        print str(self.min_val) + ' ' + str(self.max_val)

    def Clone(self):
        """Every validator must implement the Clone() method
        """
        return NumberValidator(max_val=self.max_val, min_val=self.min_val)

    def Validate(self, window):
        """ Validate the contents of a given text control
        """
        textCtrl = self.GetWindow()
        text = textCtrl.GetValue()

        insertionPointPosition = textCtrl.GetInsertionPoint()

        # remove all nondigits characters, except '.'
        text = re.sub('[^0-9.]', '', text)
        firstDot = text.find('.')
        if firstDot == 0:
            text = '0' + text
            firstDot += 1
            insertionPointPosition += 1
        if firstDot >= 0:
            #remove all '.' characters except the first
            text = text[:firstDot+1] + re.sub('[.]', '', text[firstDot+1:])

        if text != '':
            number = float(text)
            #print 'validating ' + str(self.min_val) + ' ' + str(self.max_val)
            if self.min_val != None:
                if number < self.min_val:
                    text = str(self.min_val)
                    #text = self.lastText
            if self.max_val != None:
                if number > self.max_val:
                    text = str(self.max_val)
                    #text = self.lastText
        self.lastText = text

        textCtrl.ChangeValue(text)
        #ChangeValue() function resets the position of the insertion point to 0, so we have to set it back
        textCtrl.SetInsertionPoint(insertionPointPosition)

        if len(text) == 0:
            return False

        return True

    def TransferToWindow(self):
        return True

    def TransferFromWindow(self):
        textCtrl = self.GetWindow()
        self.number = float(textCtrl.GetValue())
        return True

    def GetValue(self):
        return self.number

class NumberInputCtrl(wx.TextCtrl):
    def __init__(self, *args, **kwargs):
        self.variableName = kwargs['variableName']
        del kwargs['variableName']
        wx.TextCtrl.__init__(self, *args, **kwargs)

        self.Bind(wx.EVT_TEXT, self.OnText)

        pendulumId = self.GetGrandParent().GetGrandParent().pendulumId
        bobId = self.GetGrandParent().bobId
        self.simulationWindow = wx.FindWindowByName('simulationWindow')
        self.pendulumHandler = self.simulationWindow.GetPendulumHandler()
        self.pendulumHandler.LinkVariable(self, pendulumId, bobId, self.variableName)

        self.OnText()

    #This function will be called when the user inserts/changes/deletes a character
    def OnText(self, e=None):
        validator = self.GetValidator()
        if validator.Validate(self):
            self.pendulumHandler.SetParameter(self, float(self.GetValue()))
            if not self.simulationWindow.IsStarted():
                self.pendulumHandler.SendParameters()

    def SetParameter(self, value):
        """This function is required by the PendulumHandler class
                when an the pendulum parameters are changed from an external object
        """
        self.ChangeValue(str(value))

class VariableEditor(wxcp.PyCollapsiblePane):

    variableNames = ['m', 'l', 'a', 'v']
    variableBounds = {'m':[0, None], 'l':[0, 1500], 'a':[None, None], 'v':[0, 100]}
    defaultValues = [10, 100, 0, 0]

    def __init__(self, *args, **kwargs):
        self.bobId = kwargs['bobId']
        del kwargs['bobId']

        wxcp.PyCollapsiblePane.__init__(self, *args, **kwargs)

        # Set style
        self.SetOwnBackgroundColour(self.GetParent().GetBackgroundColour())

        # This sizer will need 3 columns: one for the spacer,
        #   one for the variable name and one for the textctrl(input field)
        self.sizer = wx.FlexGridSizer(3, wx.Size(0, 5))
        self.GetPane().SetSizer(self.sizer)

        self.pendulumId = self.GetGrandParent().pendulumId
        self.pendulumHandler = wx.FindWindowByName('simulationWindow').GetPendulumHandler()

        self.validators = dict.fromkeys(self.variableNames)
        self.SetVariables()

        self.Bind(wxcp.EVT_COLLAPSIBLEPANE_CHANGED, self.OnPaneChanged)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def SetVariables(self):
        for variableName, value in zip(self.variableNames, self.defaultValues):
            self.AddVariable(variableName, 
                value, 
                min_val=self.variableBounds[variableName][0], 
                max_val=self.variableBounds[variableName][1])

    def AddVariable(self, variableName, value='', min_val=None, max_val=None):
        self.sizer.AddSpacer(5)

        label = wx.StaticText(self.GetPane(), label=variableName + ': ')
        self.sizer.Add(label, 0)

        validator = NumberValidator(min_val=min_val, max_val=max_val)
        #validator.SetMinMax(val_min, val_max)
        self.validators[variableName] = validator
        t = NumberInputCtrl(self.GetPane(),
            value=str(value),
            style=wx.BORDER_DEFAULT,
            validator=validator,
            variableName=variableName
        )
        t.ShowNativeCaret()
        t.SetMaxLength(20)
        self.sizer.Add(t, 0)

        self.GetParent().GetParent().GetParent().SendSizeEvent()

    def OnPaneChanged(self, e):
        self.GetParent().GetParent().GetParent().SendSizeEvent()

    def GetBobId(self):
        return self.bobId

    def OnClose(self, e):
        self.pendulumHandler.RemoveBob(self.pendulumId, self.bobId)

class PendulumEditor(wxcp.PyCollapsiblePane):
    def __init__(self, pendulumId, *args, **kwargs):
        self.pendulumId = pendulumId
        wxcp.PyCollapsiblePane.__init__(self, *args, **kwargs)

        self.GetPane().SetOwnBackgroundColour(self.GetParent().GetBackgroundColour())
        button = self.prepareButton(self.GetLabel())
        button.SetLabel(self.GetLabel())
        self.SetButton(button)
        self.SetExpanderDimensions(0, 0)
        self.SetLabel('')

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.GetPane().SetSizer(self.sizer)

        self.bobCount = 0
        self.bobList = []
        self.bobDict = {}

        addBobButton = wx.Button(self.GetPane(), label='Add Bob')
        self.sizer.Add(addBobButton)

        simulationWindow = wx.FindWindowByName('simulationWindow')
        self.pendulumHandler = simulationWindow.GetPendulumHandler()
        self.pendulumHandler.LinkPendulum(self, pendulumId)

        self.sizersDict = {}

        self.sizer.Layout()

        self.Bind(wx.EVT_BUTTON, self.OnAddBobButton, addBobButton)
        self.Bind(wxcp.EVT_COLLAPSIBLEPANE_CHANGED, self.OnPaneChanged)

    def prepareButton(self, label=''):
        button = wx.Button(self, size=wx.Size(1000, 17), style=wx.BORDER_NONE|wx.BU_EXACTFIT)
        width, height = button.GetSize()

        bitmapInactive = wx.Bitmap(width, height)
        bitmapCurrent = wx.Bitmap(width, height)
        dc = wx.MemoryDC()

        # Draw the button in the inactive mode
        self.drawButton(bitmapInactive, wx.Colour(130, 130, 130), label)

        # Draw the button in the current mode(hover):
        self.drawButton(bitmapCurrent, wx.Colour(155, 155, 155), label)

        button.SetBitmap(bitmapInactive)
        button.SetBitmapCurrent(bitmapCurrent)

        return button

    def drawButton(self, bitmap, colour, label=''):
        width, height = bitmap.GetSize()
        dc = wx.MemoryDC()
        dc.SelectObjectAsSource(bitmap)
        dc.Clear()
        dc.SetBrush(wx.Brush(colour))
        dc.SetPen(wx.Pen(colour))
        dc.DrawRectangle(0, 0, width, height)
        dc.SetBrush(wx.Brush(wx.BLACK))
        dc.SetPen(wx.Pen(wx.BLACK))
        dc.DrawLabel(label, wx.Rect(2, 1, width - 6, height - 15),
            alignment=wx.ALIGN_LEFT|wx.ALIGN_TOP)

    def OnAddBobButton(self, e):
        self.AddBob()

    def AddBob(self, bobId=None):
        self.bobCount += 1

        if bobId == None:
            bobId = self.pendulumHandler.AddBob(obj=self)

        t = VariableEditor(self.GetPane(), id=wx.ID_ANY,
            label='Bob ' + str(self.bobCount),
            agwStyle=wxcp.CP_GTK_EXPANDER,
            bobId=bobId)

        t.Expand()
        self.bobDict[bobId] = t
        self.bobList.append(t)

        closeButton = wx.Button(self.GetPane(), id=bobId, size=(20, 20), label='x')

        self.Bind(wx.EVT_BUTTON, self.OnCloseButton, closeButton)

        sizer1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer1.Add(closeButton)
        sizer1.AddStretchSpacer(1)
        sizer2.Add(t, 0)
        sizer2.Add(sizer1, 1, wx.EXPAND)

        self.sizersDict[bobId] = sizer2
        self.sizer.Insert(len(self.sizer.GetChildren()) - 1, sizer2, 0)
        self.sizer.Layout()
        self.GetParent().SendSizeEvent()

    def OnCloseButton(self, e):
        self.bobCount -= 1

        bobId = e.GetId()

        self.bobDict[bobId].Close()
        sizer = self.sizersDict[bobId]
        for child in sizer.GetChildren():
            child.DeleteWindows()
        self.sizer.Remove(sizer)

        bob = self.bobDict[bobId]
        del self.bobDict[bobId]
        self.bobList.remove(bob)

        self.ResetBobIndexes()

        self.InvalidateBestSize()
        self.GetParent().SendSizeEvent()

    def ResetBobIndexes(self):
        for i in range(len(self.bobList)):
            self.bobList[i].SetLabel('Bob ' + str(i + 1))

    def OnPaneChanged(self, e):
        self.GetParent().SendSizeEvent()

class Explorer(wx.ScrolledCanvas):
    def __init__(self, *args, **kwargs):
        kwargs['name'] = 'explorer'

        wx.ScrolledCanvas.__init__(self, *args, **kwargs)

        # Set style
        self.SetBackgroundColour(wx.Colour(200, 200, 200))
        self.SetScrollbars(0, 20, 0, 50, xPos=20, yPos=0)

        self.pendulumCount = 0

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.button = wx.Button(self, label='+Add Pendulum')
        self.button.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.sizer.Add(self.button)

        self.sizer.Prepend(0, 4, 0)
        self.sizer.Prepend(wx.StaticLine(self, size=(200, 3)), 0, wx.EXPAND)
        self.sizer.Prepend(0, 4, 0)

        self.SetSizer(self.sizer)

        self.simulationWindow = wx.FindWindowByName('simulationWindow')
        self.pendulumHandler = self.simulationWindow.GetPendulumHandler()

        self.Bind(wx.EVT_BUTTON, self.OnButton, self.button)
        self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.OnCaptureLost)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeaveWindow)
        self.Bind(wx.EVT_ENTER_WINDOW, self.OnEnterWindow)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnWheel)

    def OnButton(self, e):
        self.AddPendulum(bobs=1)

    def AddPendulum(self, pendulumId=None, x=None, y=None, bobs=0):
        self.pendulumCount += 1
        if pendulumId == None:
            if x != None and y != None:
                pendulumId = self.pendulumHandler.AddPendulum(x, y)
            else:
                pendulumId = self.simulationWindow.AddPendulum()

        pane = PendulumEditor(
            pendulumId,
            self,
            label='Pendulum ' + str(self.pendulumCount),
            agwStyle=wxcp.CP_GTK_EXPANDER)

        for i in range(bobs):
            pane.AddBob()

        pane.Expand()
        self.sizer.Prepend(pane, flag=wx.EXPAND)
        self.sizer.Layout()
        self.SendSizeEvent()

        return pendulumId

    def OnCaptureLost(self, e):
        print 'capture changed'

    def OnLeaveWindow(self, e):
        pass
        #self.ReleaseMouse()
        #self.simulationWindow.SetFocus()

    def OnEnterWindow(self, e):
        pass
        #self.CaptureMouse()
        #self.SetFocus()

    def OnWheel(self, e):
        e.Skip()

class UserResizableWindow(wx.Window):
    def __init__(self, *args, **kwargs):
        wx.Window.__init__(self, *args, **kwargs)

        self.spacerSize = 10

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        explorer = Explorer(self, size=(180, 0))
        self.SetBackgroundColour(wx.Colour(180, 180, 180))
        sizer.Add(explorer, 1, wx.EXPAND)
        sizer.AddSpacer(self.spacerSize)
        self.SetSizer(sizer)
        self.SetMinSize(explorer.GetSize())

        self.sizing = False

        self.Bind(wx.EVT_MOTION, self.OnMouseMove)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnMousePress)
        self.Bind(wx.EVT_LEFT_UP, self.OnMouseRelease)
        self.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseLeave)
        self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.OnMouseCaptureLost)

    def OnMouseMove(self, e):
        x = e.GetX()
        width, height = self.GetSize()
        if self.sizing == True:
            if x > self.spacerSize:
                self.SetSize(x, height)
            elif width > self.spacerSize + 1:
                self.SetSize(self.spacerSize + 1, height)

    def OnMousePress(self, e):
        self.sizing = True
        self.CaptureMouse()

    def OnMouseRelease(self, e):
        self.sizing = False
        self.GetContainingSizer().SetItemMinSize(self, self.GetRect().width, self.GetRect().height)
        self.GetParent().Layout()
        if self.HasCapture():
            self.ReleaseMouse()

    def OnMouseEnter(self, e):
        self.SetCursor(wx.Cursor(wx.CURSOR_SIZEWE))

    def OnMouseLeave(self, e):
        if not self.sizing:
            self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))

    def OnMouseCaptureLost(self, e):
        if self.HasCapture():
            self.ReleaseMouse()

class MainFrame(wx.Frame):

    """Derive a new class from Frame"""
    def __init__(self, parent, title):
        width = 800
        height = 600

        wx.Frame.__init__(self, parent, title=title, size=(width, height),
            style=wx.DEFAULT_FRAME_STYLE ^ wx.CLIP_CHILDREN)

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

        explorerPanel = UserResizableWindow(self.simulationWindow, size=(150, 0), style=wx.BORDER_SIMPLE)

        windowSizer = wx.BoxSizer(wx.HORIZONTAL)
        windowSizer.Add(explorerPanel, 0, wx.EXPAND)
        self.simulationWindow.SetSizer(windowSizer)

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
        self.simulationWindow.Close(True)
        e.Skip()

def main():
    app = wx.App(False)
    frame = MainFrame(None, title='Pendulum Sandbox')

    frame.Show(True)
    app.MainLoop()


if __name__ == "__main__":
    main()
