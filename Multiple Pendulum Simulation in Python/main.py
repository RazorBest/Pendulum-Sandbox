"""
    This is a simulation of an n-link pendulum
"""
import os
import time
import threading
import wx
import wx.lib.agw.pycollapsiblepane as wxcp
import wx.lib.newevent
import wx.lib.scrolledpanel as wxsp
import re
from pendulum import Pendulum

class BufferedWindow(wx.Window):
    def __init__(self, *args, **kwargs):
        kwargs['style'] = kwargs.setdefault('style', wx.NO_FULL_REPAINT_ON_RESIZE | wx.NO_FULL_REPAINT_ON_RESIZE)
        wx.Window.__init__(self, *args, **kwargs)

        # Setting up the event handlers
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)

    # This funtion is for subclasses
    def Draw(self, dc):
        pass

    def UpdateDrawing(self):
        dc = wx.MemoryDC()
        dc.SelectObject(self._Buffer)
        self.Draw(dc)
        del dc
        wx.CallAfter(self.Paint)

    def OnSize(self, e=None):
        size = self.GetClientSize()
        self._Buffer = wx.Bitmap(size)
        self.UpdateDrawing()
        if e != None:
            e.Skip()

    def OnPaint(self, e=None):
        self.Draw(wx.BufferedPaintDC(self, self._Buffer))
        #e.Skip()

    # Does the same thing as OnPaint but is called by the client, not from a PaintEvent handler
    def Paint(self):
        self.Draw(wx.BufferedDC(wx.ClientDC(self), self._Buffer))

class SimulationWindow(BufferedWindow):
    main_thread = None

    def __init__(self, *args, **kwargs):
        self.ticksPerSecond = 500
        #self.pendulum = Pendulum(200, 100, 1. / self.ticksPerSecond)
        #self.pendulum.AddBob(20, 80, 2, 0)
        #self.pendulum.AddBob(20, 180, 1.5, 0)

        #kwargs['size'] = (300, 200)
        kwargs['name'] = 'simulationWindow'
        BufferedWindow.__init__(self, *args, **kwargs)

        self.running = False
        self.SetBackgroundColour(wx.WHITE)

        self.pendulumHandler = PendulumHandler()

        self.Bind(wx.EVT_LEFT_DOWN, self.OnMouseClick)
        self.Bind(wx.EVT_MOTION, self.OnMouseMove)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)

        self.clicked = False
        self.originX = 0
        self.originY = 0
        self.scale = 1
        self.lastMouseX = None
        self.lastMouseY = None

        self.movingState = False
        self.pause = True
        self.started = False

        self.timer = wx.Timer(self)

        self.Bind(wx.EVT_TIMER, self.OnTimer, self.timer)

        wx.CallLater(2000, self.StartThread)

        print "SimulationWindow initiated"

    def StartThread(self):
        self.timer.Start(1000. / 200)
        self.running = True
        self.main_thread = threading.Thread(target=self.run)
        self.main_thread.daemon = True
        self.main_thread.start()

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
        #dc.SetBackground(wx.Brush(wx.WHITE))

        #drawing the origin
        dc.SetDeviceOrigin(self.originX, self.originY)
        dc.SetUserScale(self.scale, self.scale)

        dc.DrawCircle(0, 0, 3)
        dc.DrawLine(-15, 0, 15, 0)
        dc.DrawLine(0, -15, 0, 15)

        self.pendulumHandler.Draw(dc)

    def SetPause(self, pause):
        self.pause = pause
        if pause == False:
            self.started = True
    
    def Reload(self):
        self.pause = True
        self.started = False
        self.pendulumHandler.ReleaseStack()
        self.pendulumHandler.SendParameters()
    
    def OnMouseMove(self, e):
        if self.movingState == False:
            return
        x, y = e.GetX(), e.GetY()
        if e.LeftIsDown() == True and self.lastMouseX != None and self.lastMouseY != None:
            self.originX += x - self.lastMouseX
            self.originY += y - self.lastMouseY
        self.lastMouseX = x
        self.lastMouseY = y

    def OnMouseClick(self, e):
        pass

    def OnMouseWheel(self, e):
        mag = self.scale * e.GetWheelRotation() / e.GetWheelDelta() / 20.
        mx = e.GetX()
        my = e.GetY()
        if self.scale + mag > 0:
            self.originX -= (mx - self.originX) * mag / float(self.scale)
            self.originY -= (my - self.originY) * mag / float(self.scale)
            self.scale += mag

    def GetPendulumHandler(self):
        return self.pendulumHandler

    def AddPendulum(self):
        return self.pendulumHandler.AddPendulum((300 - self.originX) / self.scale, (200 - self.originY) / self.scale, 1. / self.ticksPerSecond)

    def IsPaused(self):
        return self.pause

    def IsStarted(self):
        return self.started

class DataHolder():
    def __init__(self, val=None):
        self.val = val

    def Set(self, val):
        self.val = val 

    def Get(self):
        return self.val

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
        self.linker = {}
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

    def AddBob(self, pendulumId):
        self.bobId += 1
        if not self.simulationWindow.IsStarted():
            self.pendulumDict[pendulumId].AddBob(self.bobId)
        elif self.pendulumDict.get(pendulumId) != None:
            self.bobStack.setdefault(pendulumId, [])
            self.bobStack[pendulumId].append(self.bobId) 
        else:
            self.pendulumStack[pendulumId].AddBob(self.bobId)
        self.variableList[pendulumId][self.bobId] = self.DataDict(self.defaultVariableList)

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

    def Link(self, obj, pendulumId, bobId, name):
        self.linker[obj] = self.variableList[pendulumId][bobId][name]

    def SetParameter(self, pendulumId, bobId, name, value):
        self.variableList[pendulumId][bobId][name].val = value

    def SetParameter(self, obj, value):
        self.linker[obj].val = value

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

    def Tick(self):
        for pendulum in self.pendulumDict.values():
            pendulum.Tick()

    def Draw(self, dc):
        for pendulum in self.pendulumDict.values():
            pendulum.Draw(dc)


class NumberValidator(wx.Validator):
    def __init__(self, *args, **kwargs):
        wx.Validator.__init__(self, *args, **kwargs)

        self.number = None

    def Clone(self):
        """Every validator must implement the Clone() method
        """
        return NumberValidator()
    
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
        self.pendulumHandler.Link(self, pendulumId, bobId, self.variableName)

        self.OnText()

    #This function will be called when the user inserts/changes/deletes a character
    def OnText(self, e=None):
        validator = self.GetValidator()
        if validator.Validate(self):
            self.pendulumHandler.SetParameter(self, float(self.GetValue()))
            if not self.simulationWindow.IsStarted():
                self.pendulumHandler.SendParameters()

class VariableEditor(wxcp.PyCollapsiblePane):
    
    variableNames = ['m', 'l', 'a', 'v']
    defaultValues = [10, 100, 0, 0]

    def __init__(self, *args, **kwargs):
        wxcp.PyCollapsiblePane.__init__(self, *args, **kwargs)

        # Set style
        self.SetOwnBackgroundColour(self.GetParent().GetBackgroundColour())

        # This sizer will need 3 columns: one for the spacer,
        #   one for the variable name and one for the textctrl(input field)
        self.sizer = wx.FlexGridSizer(3, wx.Size(0, 5))
        self.GetPane().SetSizer(self.sizer)

        self.pendulumId = self.GetGrandParent().pendulumId
        self.pendulumHandler = wx.FindWindowByName('simulationWindow').GetPendulumHandler()
        self.bobId = self.pendulumHandler.AddBob(self.pendulumId)

        self.validators = dict.fromkeys(self.variableNames)
        self.SetVariables()

        self.Bind(wxcp.EVT_COLLAPSIBLEPANE_CHANGED, self.OnPaneChanged)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def SetVariables(self):
        for variableName, value in zip(self.variableNames, self.defaultValues):
            self.AddVariable(variableName, value)

    def AddVariable(self, variableName, value=''):
        self.sizer.AddSpacer(5)

        label = wx.StaticText(self.GetPane(), label=variableName + ': ')
        self.sizer.Add(label, 0)

        validator = NumberValidator()
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
    def __init__(self, *args, **kwargs):
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
        self.pendulumId = simulationWindow.AddPendulum()
        self.pendulumHandler = simulationWindow.GetPendulumHandler()

        self.sizersDict = {}

        # Only add bob after adding the addBobButton
        self.AddBob()

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
            alignment=wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_TOP)
    
    def OnAddBobButton(self, e):
        self.AddBob()

    def AddBob(self):
        self.bobCount += 1

        t = VariableEditor(self.GetPane(), id=wx.ID_ANY, 
            label='Bob ' + str(self.bobCount),
            agwStyle=wxcp.CP_GTK_EXPANDER)
        t.Expand()
        bobId = t.GetBobId()
        self.bobDict[bobId] = t
        self.bobList.append(t)

        closeButton = wx.Button(self.GetPane(), id=bobId, size=(20, 20), label='t')

        self.Bind(wx.EVT_BUTTON, self.OnCloseButton, closeButton)

        sizer1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer1.Add(closeButton)
        sizer1.AddStretchSpacer(1)
        sizer2.Add(t, 0)
        sizer2.Add(sizer1, 1, wx.EXPAND)

        self.sizersDict[bobId] = sizer2

        self.sizer.Insert(len(self.sizer.GetChildren()) - 1, sizer2, 0)

        self.GetParent().SendSizeEvent()

    def OnCloseButton(self, e):
        self.bobCount -= 1

        bobId = e.GetId()

        self.bobDict[bobId].Close()
        #self.pendulumHandler.RemoveBob(self.pendulumId, bobId)
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

class Explorer(wx.ScrolledWindow):
    def __init__(self, *args, **kwargs):
        wx.ScrolledWindow.__init__(self, *args, **kwargs)

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

        self.Bind(wx.EVT_BUTTON, self.OnButton, self.button)

    def OnButton(self, e):
        self.pendulumCount += 1
        pane = PendulumEditor(self, 
            label='Pendulum ' + str(self.pendulumCount), 
            agwStyle=wxcp.CP_GTK_EXPANDER)
        pane.Expand()
        self.sizer.Prepend(pane, flag=wx.EXPAND)
        self.Refresh()
        self.Layout()

class UserResizableWindow(wx.Window):
    def __init__(self, *args, **kwargs):
        wx.Window.__init__(self, *args, **kwargs)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        explorer = Explorer(self, size=(180, 0))
        self.SetBackgroundColour(wx.Colour(180, 180, 180))
        sizer.Add(explorer, 1, wx.EXPAND)
        sizer.AddSpacer(10)
        self.SetSizer(sizer)
        self.SetMinSize(explorer.GetSize())

        self.sizing = False

        self.Bind(wx.EVT_MOTION, self.OnMouseMove)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnMousePress)
        self.Bind(wx.EVT_LEFT_UP, self.OnMouseRelease)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseLeave)
        self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.OnMouseCaptureLost)

    def OnMouseMove(self, e):
        x = e.GetX()
        width, height = self.GetSize()
        if (x >= width - 8):
            self.SetCursor(wx.Cursor(wx.CURSOR_SIZEWE))
        else:
            self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
        if self.sizing == True and x + 7 > 10:
            self.SetSize(x + 7, height)


    def OnMousePress(self, e):
        x = e.GetX()

        width = self.GetSize()[0]
        if (x >= width - 8):
            self.sizing = True
            self.CaptureMouse()

    def OnMouseRelease(self, e):
        self.sizing = False
        self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
        self.GetContainingSizer().SetItemMinSize(self, self.GetRect().width, self.GetRect().height)
        self.GetParent().Layout()
        if self.HasCapture():
            self.ReleaseMouse()
    
    def OnMouseLeave(self, e):
        if not self.sizing:
            self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))

    def OnMouseCaptureLost(self, e):
        print 'lost'
        if self.HasCapture():
            self.ReleaseMouse()

    def OnMouseCaptureChanged(self, e):
        print 'changed'

class FillWindow(wx.Window):
    def __init__(self, *args, **kwargs):
        wx.Window.__init__(self, *args, **kwargs)

        self.Bind(wx.EVT_MOTION, self.OnMouse)

    def ChangeCursor(self, stockCursor):
        self.SetCursor(wx.Cursor(stockCursor))
        if stockCursor == wx.CURSOR_ARROW:
            self.GetParent().movingState = False
        elif stockCursor == wx.CURSOR_SIZING:
            self.GetParent().movingState = True

    #Send all the mouse events to the parent i.e the SimulationWindow
    def OnMouse(self, e):
        self.GetParent().SafelyProcessEvent(e)
        e.Skip()

class MainFrame(wx.Frame):

    """Derive a new class from Frame"""
    def __init__(self, parent, title):
        width = 800
        height = 600

        wx.Frame.__init__(self, parent, title=title, size=(width, height),
            style=wx.DEFAULT_FRAME_STYLE ^ wx.CLIP_CHILDREN)

        #self.CreateStatusBar() # A Statusbar in the bottom of the frame

        #Setting up the menu
        filemenu = wx.Menu()

        # wx.ID_ABOUT and wx.ID_EXIT are standards provided by wxWidgets
        menuOpen = filemenu.Append(wx.ID_OPEN, "Open", "Open a file from the system")
        filemenu.AppendSeparator()
        menuAbout = filemenu.Append(wx.ID_ABOUT, "About", "Information about this program")
        filemenu.AppendSeparator()
        menuExit = filemenu.Append(wx.ID_EXIT, "Exit", "Terminate the program")

        # Creating the menubar
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu, "File") # Adding the "filemenu" to the MenuBar
        #self.SetMenuBar(menuBar) # Adding the MenuBar to the Frame content

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
        self.Bind(wx.EVT_MENU, self.OnOpen, menuOpen)
        self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
        self.Bind(wx.EVT_MENU, self.OnExit, menuExit)
        self.Bind(wx.EVT_TOOL, self.OnChangeCursor, self.selectionTool)
        self.Bind(wx.EVT_TOOL, self.OnChangeCursor, self.moveTool)
        self.Bind(wx.EVT_TOOL, self.OnTogglePlay, self.playTool)
        self.Bind(wx.EVT_TOOL, self.OnTogglePlay, self.pauseTool)
        self.Bind(wx.EVT_TOOL, self.OnReload, self.reloadTool)

        self.window = SimulationWindow(self, size=(width, 0))
        self.fillWindow = FillWindow(self.window, style=wx.TRANSPARENT_WINDOW)

        explorerPanel = UserResizableWindow(self.window, size=(150, 0), style=wx.BORDER_SIMPLE)
        windowSizer = wx.BoxSizer(wx.HORIZONTAL)
        windowSizer.Add(explorerPanel, 0, wx.EXPAND)

        windowSizer.Add(self.fillWindow, 1, wx.EXPAND)
        self.window.SetSizer(windowSizer)

        self.Centre()
        self.Show(True)

    def OnChangeCursor(self, e):
        id = e.GetId()
        if id == self.selectionTool.GetId():
            self.fillWindow.ChangeCursor(wx.CURSOR_ARROW)
        elif id == self.moveTool.GetId():
            #print 'ahoy'
            self.fillWindow.ChangeCursor(wx.CURSOR_SIZING)
            #self.ChangeCursor(wx.CURSOR_SIZING)

    def OnTogglePlay(self, e):
        id = e.GetId()
        if id == self.playTool.GetId():
            self.window.SetPause(False)
        elif id == self.pauseTool.GetId():
            self.window.SetPause(True)

    def OnReload(self, e):
        self.GetToolBar().ToggleTool(self.pauseTool.GetId(), True)
        self.window.Reload()

    def OnAbout(self, e):
        # A message dialog box with an OK button. wx.OK is a standard ID in wxWidgets
        dlg = wx.MessageDialog(self, "A small editor", "About Sample Editor", wx.OK)
        dlg.ShowModal() # show it
        dlg.Destroy() # finally destroy it when finished

    def OnExit(self, e):
        self.Close(True)

    def OnOpen(self, e):
        """Open a file"""
        self.dirname = ''
        dlg = wx.FileDialog(self, "Choose a file", self.dirname, "", "*.*", wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.filename = dlg.GetFilename()
            self.dirname = dlg.GetDirectory()
            f = open(os.path.join(self.dirname, self.filename), 'r')
            self.control.SetValue(f.read())
            f.close()
        dlg.Destroy()

def main():
    app = wx.App(False)
    frame = MainFrame(None, title='Pendulum Sandbox')

    #drawingPanel = MyPanel(frame, -1)
    #drawingPanel.Bind(wx.EVT_PAINT, draw)

    frame.Show(True)
    app.MainLoop()


if __name__ == "__main__":
    main()
