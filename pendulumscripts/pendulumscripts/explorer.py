import re
import wx
import wx.lib.newevent
import wx.lib.agw.pycollapsiblepane as wxcp

#Here we create our custom event classes
PendulumCreationStartEvent, EVT_PENDULUM_CREATION_START = wx.lib.newevent.NewEvent()
PendulumCreationReadyEvent, EVT_PENDULUM_CREATION_READY = wx.lib.newevent.NewEvent()
BobCreationStartEvent, EVT_BOB_CREATION_START = wx.lib.newevent.NewEvent()
BobCreationReadyEvent, EVT_BOB_CREATION_READY = wx.lib.newevent.NewEvent()
BobVariablesUpdateEvent, EVT_BOB_VARIABLES_UPDATE = wx.lib.newevent.NewEvent()

def prepareButton(parent, inactiveBgColour, currentBgColour, label='', width=20, height=20):
    button = wx.Button(parent, size=wx.Size(width, height), style=wx.BORDER_NONE|wx.BU_EXACTFIT)

    bitmapInactive = wx.Bitmap(width, height)
    bitmapCurrent = wx.Bitmap(width, height)

    # Draw the button in the inactive mode
    drawButton(bitmapInactive, inactiveBgColour, label)

    # Draw the button in the current mode(hover):
    drawButton(bitmapCurrent, currentBgColour, label)

    button.SetBitmap(bitmapInactive)
    button.SetBitmapCurrent(bitmapCurrent)

    return button 

def drawButton(bitmap, colour, label=''):
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

        # remove all nondigits characters, except '.' and '-'
        text = re.sub('[^0-9.-]', '', text)
        # remove all '-' characters that are not the first
        text = text[:1] + re.sub('[-]', '', text[1:])

        firstDot = text.find('.')
        if firstDot == 0 or (firstDot == 1 and text[0] == '-'):
            text = text[:firstDot] + '0' + text[firstDot:]
            firstDot += 1
            insertionPointPosition += 1
        if firstDot >= 0:
            #remove all '.' characters except the first
            text = text[:firstDot+1] + re.sub('[.]', '', text[firstDot+1:])

        isNumber = False
        if text != '' and re.search('[0-9]', text) != None:
            isNumber = True
            number = float(text)
            # Check boundaries
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

        if not isNumber:
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
    def __init__(self, parent, **kwargs):
        if not 'min_val' in kwargs:
            kwargs['min_val'] = None
        if not 'max_val' in kwargs:
            kwargs['max_val'] = None
        kwargs['validator'] = NumberValidator(min_val=kwargs['min_val'], max_val=kwargs['max_val'])
        del kwargs['min_val']
        del kwargs['max_val']
        wx.TextCtrl.__init__(self, parent, **kwargs)

        self.Bind(wx.EVT_TEXT, self.OnText)

    # This function will be called when the user inserts/changes/deletes a character
    def OnText(self, e=None):
        validator = self.GetValidator()
        if validator.Validate(self):
            self.OnUpdateVariable(float(self.GetValue()))
        
    # This function will be implemented by subclasses
    def OnUpdateVariable(self, value):
        pass

    def SetParameter(self, value):
        """This function is required by the PendulumHandler class
                when an the pendulum parameters are changed from an external object
        """
        self.ChangeValue(str(value))

class BobVariableInputCtrl(NumberInputCtrl):
    """Specialization class for NumberInputCtrl, made for bob variables"""
    def __init__(self, parent, pendulumHandler, **kwargs):
        self.variableName = kwargs['variableName']
        del kwargs['variableName']
        NumberInputCtrl.__init__(self, parent, **kwargs)

        pendulumId = self.GetGrandParent().GetGrandParent().pendulumId
        bobId = self.GetGrandParent().bobId
        self.simulationWindow = wx.FindWindowByName('simulationWindow') # This should not be here
        self.pendulumHandler = pendulumHandler
        self.pendulumHandler.LinkVariable(self, pendulumId, bobId, self.variableName)

        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.OnText()

    #This function will be called from the parrent class when the user inserts/changes/deletes a character
    def OnUpdateVariable(self, value):
        self.pendulumHandler.SetParameter(self, float(self.GetValue()))
        if not self.simulationWindow.IsStarted():   # This should not be here
            self.pendulumHandler.SendParameters() 

    def OnClose(self, e):
        self.pendulumHandler.UnlinkVariable(self)

class TimeIntervalInputCtrl(NumberInputCtrl):
    def __init__(self, parent, pendulumHandler, pendulumId, **kwargs):
        NumberInputCtrl.__init__(self, parent, **kwargs)

        self.pendulumId = pendulumId
        self.pendulumHandler = pendulumHandler

    #This function will be called from the parrent class when the user inserts/changes/deletes a character
    def OnUpdateVariable(self, value):
        self.pendulumHandler.SetTimeInterval(value, self.pendulumId)


class VariableEditor(wxcp.PyCollapsiblePane):

    variableNames = ['m', 'l', 'a', 'v']
    variableBounds = {'m':[0, None], 'l':[0, 1500], 'a':[None, None], 'v':[0, 100]}
    defaultValues = [10, 100, 0, 0]

    def __init__(self, parent, pendulumHandler, **kwargs):
        self.bobId = kwargs['bobId']
        del kwargs['bobId']
        valueDict = kwargs['valueDict']
        del kwargs['valueDict']

        wxcp.PyCollapsiblePane.__init__(self, parent, **kwargs)

        # Set style
        self.SetOwnBackgroundColour(self.GetParent().GetBackgroundColour())

        # This sizer will need 3 columns: one for the spacer,
        #   one for the variable name and one for the textctrl(input field)
        self.sizer = wx.FlexGridSizer(3, wx.Size(0, 5))
        self.GetPane().SetSizer(self.sizer)

        self.pendulumId = self.GetGrandParent().pendulumId
        self.pendulumHandler = pendulumHandler
        
        if valueDict != None:
            self.variableNames = list(valueDict.keys())
            self.defaultValues = []
            for key in self.variableNames:
                self.defaultValues.append(valueDict[key])

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

        t = BobVariableInputCtrl(
            self.GetPane(),
            self.pendulumHandler,
            value=str(value),
            style=wx.BORDER_DEFAULT,
            min_val=min_val,
            max_val=max_val,
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
        print "Removed bob with id " + str(self.bobId)
        self.pendulumHandler.RemoveBob(self.pendulumId, self.bobId)
        for child in self.GetPane().GetChildren():
            child.Close()

class PendulumEditor(wxcp.PyCollapsiblePane):
    def __init__(self, pendulumId, parent, pendulumHandler, **kwargs):
        wxcp.PyCollapsiblePane.__init__(self, parent, **kwargs)

        self.pendulumId = pendulumId

        self.GetPane().SetOwnBackgroundColour(self.GetParent().GetBackgroundColour())
        button = prepareButton(self, wx.Colour(130, 130, 130), wx.Colour(155, 155, 155), self.GetLabel(), 100, 17)
        button.SetLabel(self.GetLabel())
        self.SetButton(button)
        self.SetExpanderDimensions(0, 0)
        self.SetLabel('')
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.GetPane().SetSizer(self.sizer)

        self.bobCount = 0
        self.bobList = []
        self.bobDict = {}

        # Add the input text for the time interval of the pendulum
        inputSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.updateIntervalLabel = wx.StaticText(
            self.GetPane(), 
            label='Update interval: ', 
            style=wx.ST_ELLIPSIZE_END)
        self.updateIntervalLabel.SetMaxSize(self.updateIntervalLabel.GetSize())
        self.updateIntervalInput = TimeIntervalInputCtrl(self.GetPane(), pendulumHandler, pendulumId, min_val=0, max_val=1)
        self.updateIntervalInput.ShowNativeCaret()
        self.updateIntervalInput.SetMaxLength(20)
        inputSizer.Add(self.updateIntervalLabel)
        inputSizer.Add(self.updateIntervalInput)
        self.sizer.Add(inputSizer)
        self.sizer.Layout()

        # Add the button used for appending bobs on the pendulum
        addBobButton = wx.Button(self.GetPane(), label='Add Bob')
        self.sizer.Add(addBobButton)
        self.sizer.Layout()

        self.pendulumHandler = pendulumHandler
        self.pendulumHandler.LinkPendulum(self, pendulumId)

        self.sizersDict = {}

        self.Bind(wx.EVT_BUTTON, self.OnAddBobButton, addBobButton)
        self.Bind(wxcp.EVT_COLLAPSIBLEPANE_CHANGED, self.OnPaneChanged)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(EVT_BOB_CREATION_READY, self.OnBobReady)
        self.Bind(EVT_BOB_VARIABLES_UPDATE, self.OnBobVariablesUpdate)

        #self.GetParent().Bind(wx.EVT_SIZE, self.OnSizeParent)
        self.cnt = 0

    def OnSizeParent(self, e):
        self.cnt += 1
        if self.cnt > 10:
            minWidth = e.Size.Width - self.updateIntervalInput.Rect.Width
            self.updateIntervalLabel.SetMinSize((min(self.updateIntervalLabel.MaxWidth, minWidth), 20))
        e.Skip()

    def OnAddBobButton(self, e):
        pendulumEvent = BobCreationStartEvent(
            pendulumId=self.pendulumId,
            values=None)
        wx.PostEvent(self.pendulumHandler, pendulumEvent)

    def OnBobReady(self, e):
        """This function is called after PendulumHandler finishes creating the bob"""
        bobEditor = self.AddBob(e.bobId, e.valueDict)

    def OnBobVariablesUpdate(self, e):
        pass

    def AddBob(self, bobId, valueDict):
        self.bobCount += 1

        t = VariableEditor(
            self.GetPane(), 
            self.pendulumHandler,
            id=wx.ID_ANY,
            label='Bob ' + str(self.bobCount),
            agwStyle=wxcp.CP_GTK_EXPANDER,
            bobId=bobId,
            valueDict=valueDict)

        t.Expand()
        self.bobDict[bobId] = t
        self.bobList.append(t)

        closeButton = wx.Button(self.GetPane(), id=bobId, size=(20, 20), label='x')

        self.Bind(wx.EVT_BUTTON, self.OnCloseButton, closeButton)

        sizer1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer1.Add(closeButton)
        sizer1.AddStretchSpacer(1)
        sizer2.Add(sizer1, 1, wx.EXPAND)
        sizer2.Add(t, 0)

        self.sizersDict[bobId] = sizer2
        self.sizer.Insert(len(self.sizer.GetChildren()) - 1, sizer2, 0)
        self.sizer.Layout()
        self.GetParent().SendSizeEvent()

        return t

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

    def OnClose(self, e):
        for bobEditor in self.bobDict.values():
            bobEditor.Close()
        self.pendulumHandler.RemovePendulum(self.pendulumId)

class Explorer(wx.ScrolledCanvas):
    def __init__(self, parent, pendulumHandler, **kwargs):
        kwargs['name'] = 'explorer'

        wx.ScrolledCanvas.__init__(self, parent, **kwargs)

        # Set style
        self.SetBackgroundColour(wx.Colour(200, 200, 200))
        self.SetScrollbars(0, 20, 0, 50, xPos=20, yPos=0)

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        #Creates the button object
        self.button = wx.Button(self, label='+Add Pendulum')
        #Styles the button
        self.button.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        #Adds the button to the sizer so it can be positioned
        self.sizer.Add(self.button)

        self.sizer.Prepend(0, 4, 0)
        self.sizer.Prepend(wx.StaticLine(self, size=(200, 3)), 0, wx.EXPAND)
        self.sizer.Prepend(0, 4, 0)

        self.SetSizer(self.sizer)

        self.pendulumCount = 0
        self.pendulumEditorDict = {}
        self.pendulumCloseButtonDict = {}

        self.pendulumHandler = pendulumHandler

        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_BUTTON, self.OnButton, self.button)
        self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.OnCaptureLost)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeaveWindow)
        self.Bind(wx.EVT_ENTER_WINDOW, self.OnEnterWindow)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnWheel)
        self.Bind(EVT_PENDULUM_CREATION_READY, self.OnPendulumReady)
        self.Bind(EVT_BOB_CREATION_READY, self.OnBobReady)

    def PrepareButton(self):
        pass

    def OnButton(self, e):
        #Send the event to the PendulumHandler
        pendulumEvent = PendulumCreationStartEvent(x=None, y=None)
        wx.PostEvent(self.pendulumHandler, pendulumEvent)

    def OnPendulumReady(self, e):
        self.AddPendulum(e.pendulumId)

    def OnBobReady(self, e):
        wx.PostEvent(self.pendulumEditorDict[e.pendulumId], e)

    def AddPendulum(self, pendulumId, x=None, y=None, bobs=0):
        """This function creates the pendulum editor inside the explorer panel, 
            liking it with the pendulum on the simulation window"""

        self.pendulumCount += 1
        """if pendulumId == None:
            if x != None and y != None:
                pendulumId = self.pendulumHandler.AddPendulum(x, y)
            else:
                pendulumId = self.simulationWindow.AddPendulum()
        """

        pane = PendulumEditor(
            pendulumId,
            self,
            self.pendulumHandler,
            label='Pendulum ' + str(self.pendulumCount),
            agwStyle=wxcp.CP_GTK_EXPANDER)
        self.Bind(wx.EVT_SIZE, pane.OnSizeParent)
        self.pendulumEditorDict[pendulumId] = pane

        #for i in range(bobs):
        #    pane.AddBob() #Should send an event to pendulumHandler

        pane.Expand()
        pane.SetMaxSize(wx.Size(500, -1))
        
        closeButton = prepareButton(self, wx.Colour(130, 130, 130), wx.Colour(155, 155, 155), 'x', 17, 17)

        #Position the button and the pendulum panel
        horizontalSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer = wx.BoxSizer(wx.VERTICAL)
        buttonSizer.AddSpacer(4)
        buttonSizer.Add(closeButton)
        horizontalSizer.Add(buttonSizer)
        horizontalSizer.Add(pane)
        self.sizer.Prepend(horizontalSizer)
        self.SendSizeEvent()

        #Set the event for the button
        self.Bind(wx.EVT_BUTTON, self.OnRemovePendulumButton, closeButton)

        self.pendulumCloseButtonDict[closeButton.GetId()] = {"pane":pane, "sizer":horizontalSizer}

        return pendulumId

    def OnSize(self, e):
        self.Refresh()

    def OnRemovePendulumButton(self, e):
        pane = self.pendulumCloseButtonDict[e.GetId()]["pane"]
        sizer = self.pendulumCloseButtonDict[e.GetId()]["sizer"]
        self.Unbind(wx.EVT_SIZE, handler=pane.OnSizeParent)
        pane.Close()
        for child in sizer.GetChildren():
            child.DeleteWindows()
        self.sizer.Remove(sizer)

        self.sizer.Layout()

    def OnCaptureLost(self, e):
        pass
        #print 'capture changed'

    def OnLeaveWindow(self, e):
        pass
        #These might be for the Windows 7 zoom bug
        #self.ReleaseMouse()
        #self.simulationWindow.SetFocus()

    def OnEnterWindow(self, e):
        pass
        #self.CaptureMouse()
        #self.SetFocus()

    def OnWheel(self, e):
        e.Skip()

class UserResizableWindow(wx.Window):
    def __init__(self, parent, pendulumHandler, **kwargs):
        wx.Window.__init__(self, parent, **kwargs)

        self.spacerSize = 10

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        explorer = Explorer(self, pendulumHandler, size=(self.GetSize().GetWidth(), 0))
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
        self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
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
