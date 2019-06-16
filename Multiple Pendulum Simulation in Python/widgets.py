import wx
import wx.lib.newevent
from wx.adv import PseudoDC
from buffered import BufferedWindow

FrictionUpdateEvent, EVT_FRICTION_UPDATE = wx.lib.newevent.NewEvent()

def SkipMouseEvents(window):
    window.Bind(wx.EVT_MOTION, OnSkipMouseEvent)
    window.Bind(wx.EVT_LEFT_DOWN, OnSkipMouseEvent)
    window.Bind(wx.EVT_LEFT_UP, OnSkipMouseEvent)
    window.Bind(wx.EVT_ENTER_WINDOW, OnSkipMouseEvent)
    window.Bind(wx.EVT_LEAVE_WINDOW, OnSkipMouseEvent)
    window.Bind(wx.EVT_MOUSE_CAPTURE_LOST, OnSkipMouseEvent)
    window.Bind(wx.EVT_MOUSE_EVENTS, OnSkipMouseEvent)

    for child in window.GetChildren():
        SkipMouseEvents(child)

def OnSkipMouseEvent(e):
    parent = e.GetEventObject().GetParent()
    e.Position = parent.ScreenToClient(e.GetEventObject().ClientToScreen(e.Position))
    wx.PostEvent(parent, e)

class LiveObject():
    """This class handles an object that can be updated repeatedly within a given time interval"""
    def __init__(self, ticksPerUpdate):
        self.ticksPerUpdate = ticksPerUpdate

        self.ticks = 0

    def UpdateData(self):
        """This function should be implemented by subclasses"""
        pass

    def Tick(self):
        self.ticks += 1
        if self.ticks >= self.ticksPerUpdate:
            self.ticks = 0
            self.UpdateData()

    @property
    def ticksPerUpdate(self):
        return self.__ticksPerUpdate
    
    @ticksPerUpdate.setter
    def ticksPerUpdate(self, ticksPerUpdate):
        self.__ticksPerUpdate = ticksPerUpdate

class UserResizableWindow(wx.Window):
    INVALID_POSITION = 0
    TOP_POSITION = 1
    BOTTOM_POSITION = 2
    RIGHT_POSITION = 4
    LEFT_POSITION = 8

    def __init__(
            self, parent, 
            topSpace=10, rightSpace=10, bottomSpace=10, leftSpace=10, 
            minWidth=10, minHeight=10, maxWidth=10, maxHeight=10,
            **kwargs):
        wx.Window.__init__(self, parent, **kwargs)

        self.resizableBarSpace = 35
        self.topSpace = topSpace
        self.rightSpace = rightSpace
        self.bottomSpace = bottomSpace
        self.leftSpace = leftSpace

        self.minWidth = minWidth
        self.minHeight = minHeight
        self.maxWidth = maxWidth
        self.maxHeight = maxHeight

        self.sizing = False
        self.positionCode = self.INVALID_POSITION

        # A dictionary that maps a cursor state with the cursor image to be displayed
        # The cursor state is a concatenation of position codes (eg. TOP_POSITION, LEFT_POSITION...)
        self.cursorMap = {
            self.INVALID_POSITION:wx.Cursor(wx.CURSOR_ARROW),
            self.TOP_POSITION:wx.Cursor(wx.CURSOR_SIZENS),
            self.BOTTOM_POSITION:wx.Cursor(wx.CURSOR_SIZENS),
            self.LEFT_POSITION:wx.Cursor(wx.CURSOR_SIZEWE),
            self.RIGHT_POSITION:wx.Cursor(wx.CURSOR_SIZEWE),
            self.TOP_POSITION|self.RIGHT_POSITION:wx.Cursor(wx.CURSOR_SIZENESW),
            self.BOTTOM_POSITION|self.LEFT_POSITION:wx.Cursor(wx.CURSOR_SIZENESW),
            self.TOP_POSITION|self.LEFT_POSITION:wx.Cursor(wx.CURSOR_SIZENWSE),
            self.BOTTOM_POSITION|self.RIGHT_POSITION:wx.Cursor(wx.CURSOR_SIZENWSE)
            }

        self.Bind(wx.EVT_MOTION, self.OnMouseMove)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnMousePress)
        self.Bind(wx.EVT_LEFT_UP, self.OnMouseRelease)
        self.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseLeave)
        self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.OnMouseCaptureLost)

    def GetCursorPositionCode(self, mx, my):
        width, height = self.GetSize()
        positionCode = 0
        if mx <= self.leftSpace:
            positionCode |= self.LEFT_POSITION
        elif mx >= width - self.rightSpace:
            positionCode |= self.RIGHT_POSITION
        if my <= self.topSpace:
            positionCode |= self.TOP_POSITION
        elif my >= height - self.bottomSpace:
            positionCode |= self.BOTTOM_POSITION

        return positionCode

    def OnMouseMove(self, e):
        if not self.sizing:
            self.positionCode = self.GetCursorPositionCode(e.x, e.y)
            self.SetCursor(self.cursorMap[self.positionCode])
        #width, height = self.GetSize()
        if self.sizing == True:
            if self.positionCode & self.RIGHT_POSITION:
                x, y = e.x, e.y
                width, height = self.GetSize()

                if x >= self.minWidth:
                    self.SetSize(x, height)

            if self.positionCode & self.BOTTOM_POSITION:
                x, y = e.x, e.y
                width, height = self.GetSize()

                if y >= self.minHeight:
                    self.SetSize(width, y)

            if self.positionCode & self.LEFT_POSITION:
                x, y = self.ClientToScreen(e.x, e.y)
                parent = self.GetParent()
                x, y = parent.ScreenToClient(x, y)
                width, height = self.GetSize()
                posX, posY = self.GetPosition()

                if e.x <= width - self.minWidth:
                    self.SetPosition((x, posY))
                    self.SetSize(width + posX - x, height)

            if self.positionCode & self.TOP_POSITION:
                x, y = self.ClientToScreen(e.x, e.y)
                parent = self.GetParent()
                x, y = parent.ScreenToClient(x, y)
                width, height = self.GetSize()
                posX, posY = self.GetPosition()

                if e.y <= height - self.minHeight:
                    self.SetPosition((posX, y))
                    self.SetSize(width, height + posY - y)

    def OnMousePress(self, e):
        if self.positionCode != self.INVALID_POSITION and not self.HasCapture():
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
        if not self.sizing:
            self.positionCode = self.GetCursorPositionCode(e.x, e.y)
            self.SetCursor(self.cursorMap[self.positionCode])

    def OnMouseLeave(self, e):
        if not self.sizing:
            self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))

    def OnMouseCaptureLost(self, e):
        if self.HasCapture():
            self.ReleaseMouse()

class EnergyDisplayScreen(wx.Window, LiveObject):
    def __init__(self, parent, ticksPerUpdate=1, scale=10, extension=None, **kwargs):
        wx.Window.__init__(self, parent, **kwargs)
        LiveObject.__init__(self, ticksPerUpdate)

        self._extension = extension
        self.scale = scale

        self._minVal = 0
        self._maxVal = 10
        self.markerCount = 5
        self.markerLength = 20
        self.minLimit = 10

        self.timeAxisY = 20

        self.topSpace = 15
        self.originX = 50
        self.originY = self.timeAxisY + 10

        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        
        self.clear = True

    def UpdateData(self):
        potential = self.extension.GetPotentialEnergy()
        kinetic = self.extension.GetKineticEnergy()
        total = potential + kinetic
        self.AddValue('potential', potential)
        self.AddValue('kinetic', kinetic)
        self.AddValue('total', total)

        width, height = self.GetSize()
        n = len(self.extension.data['potential'].values)
        while self.scale * (n + 3) > width:
            self.clear = True
            for data in self.extension.data.values():
                data.values.pop(0)
            n = len(self.extension.data['potential'].values)

        #self.Refresh()
        #Update the paint
        dc = wx.ClientDC(self)
        self.Draw(dc)

    def DrawMarkers(self, dc):
        width, height = self.GetSize()

        limit = max(self.minLimit + self.originX, height - self.topSpace)

        y = self.originY
        unit = (limit - self.originY) * 1. / self.markerCount

        # Draw the y axis
        dc.DrawLine(self.originX, height - self.timeAxisY, self.originX, 0)

        # Draw the markers on the y axis
        while y <= limit:
            value = (y - self.originY) * 1. / (limit - self.originY) * (self.maxVal - self.minVal) + self.minVal
            
            text = "%.1f" % (value) + " J"
            textWidth, textHeight = dc.GetTextExtent(text)
            dc.DrawText(text, self.originX - self.markerLength / 2 - textWidth - 4, height - y - textHeight / 2)
            dc.DrawLine(self.originX - self.markerLength / 2, height - y, self.originX + self.markerLength / 2, height - y)
            y += unit

        #Draw the x axis
        dc.DrawLine(0, height - self.timeAxisY, width, height - self.timeAxisY)

    def Draw(self, dc):
        dc.SetPen(wx.Pen(wx.Colour(wx.BLACK)))
        dc.SetBrush(wx.Brush(wx.Colour(wx.BLACK)))
        
        dc.SetBackground(wx.Brush(wx.Colour(wx.WHITE)))
        dc.Clear()
        # Draws the x axis, the y axis and all the markers along them
        self.DrawMarkers(dc)

        if self.extension == None:
            return

        width, height = self.GetSize()
        limit = max(self.minLimit + self.originX, height - self.topSpace)
        interval = self.maxVal - self.minVal
        
        newMaxVal = None
        newMinVal = None 

        for data in self.extension.data.values():
            values = data.values

            points = []
            for i in range(len(values)):
                x = i * self.scale + self.originX
                y = height - values[i] * 1. / interval * (limit - self.originY) - self.originY
                points.append(wx.Point(x, y))

                if newMaxVal == None:
                    newMaxVal = values[i]
                if newMinVal == None:
                    newMinVal = values[i]
                newMaxVal = max(values[i], newMaxVal)
                newMinVal = min(values[i], newMinVal)

            if len(values) > 2:
                dc.SetBrush(wx.Brush(data.color))
                dc.SetPen(wx.Pen(data.color))
                dc.DrawSpline(points)

        if newMaxVal != None:
            self.maxVal = newMaxVal
        if newMinVal != None:
            self.minVal = newMinVal

        """
        self.dataIterator = 1
        i = None
        for data in self.extension.data.values():
            
            values = data.values

            i = self.dataIterator

            lastY = values[i - 1] * 1. / interval * (height - self.originY) + self.originY
            lastX = (i - 1) * self.scale + self.originX
            
            while i < len(values):
                y = values[i] * 1. / interval * (height - self.originY) + self.originY
                x = i * self.scale + self.originX
                dc.SetBrush(wx.Brush(data.color))
                dc.SetPen(wx.Pen(data.color))
                dc.DrawLine(lastX, height - lastY, x, height - y)
                lastX = x
                lastY = y
                i += 1

        self.dataIterator = i"""

    def OnPaint(self, e):
        self.clear = True
        dc = wx.PaintDC(self)
        self.Draw(dc)
        e.Skip()

    def OnSize(self, e):
        self.clear = True
        dc = wx.ClientDC(self)
        self.Draw(dc)
        e.Skip()

    def AddValue(self, key, value):
        self.extension.data[key].values.append(value)
        if (value > self.maxVal):
            self.maxVal = value
            self.clear = True
        if value < self._minVal:
            self.minVal = value
            self.clear = True

    def UpdateOriginX(self, dc):
        pass

    def UpdateMinMax(self):
        newMinVal = None
        newMaxVal = None
        for data in self.extension.data.values():
            values = data.values
            for value in values:
                if newMinVal == None:
                    newMinVal = value
                if newMaxVal == None:
                    newMaxVal = value
                newMinVal = min(newMinVal, value)
                newMaxVal = max(newMaxVal, value)

        self.maxVal = newMaxVal
        self.minVal = newMinVal

    @property
    def extension(self):
        return self._extension

    @extension.setter
    def extension(self, extension):
        self._extension = extension
        self.UpdateMinMax()
        # Repaint
        dc = wx.ClientDC(self)
        self.Draw(dc)

    @property
    def minVal(self):
        return self._minVal

    @minVal.setter
    def minVal(self, minVal):
        if self.maxVal - minVal > 10:
            self._minVal = minVal
        else:
            self._minVal = self.maxVal - 10

    @property
    def maxVal(self):
        return self._maxVal

    @maxVal.setter
    def maxVal(self, maxVal):
        if maxVal - self.minVal > 10:
            self._maxVal = maxVal
        else:
            self._maxVal = self.minVal + 10

class EnergyDisplay(UserResizableWindow):
    def __init__(self, parent, ticksPerUpdate=1, scale=10, extension=None, **kwargs):
        UserResizableWindow.__init__(self, parent, 15, -1, -1, -1, 20, 20, **kwargs)
        
        self.screen = EnergyDisplayScreen(self, ticksPerUpdate, scale, extension, style=wx.STATIC_BORDER)
        
        self.topBar = wx.Window(self, size=(0, 20))
        self.topBar.SetBackgroundColour(wx.Colour(90, 90, 100))

        SkipMouseEvents(self.screen)
        SkipMouseEvents(self.topBar)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.topBar, flag=wx.EXPAND)
        self.sizer.AddSpacer(5)
        self.sizer.Add(self.screen, 1, wx.EXPAND)
        self.sizer.Layout()
        self.SetSizer(self.sizer)

        self.Bind(wx.EVT_SIZE, self.OnSize)

    def OnSize(self, e):
        self.Refresh()
        e.Skip()

    def Tick(self):
        self.screen.Tick()

    def Draw(self, dc):
        self.screen.Draw(dc)

    @property
    def extension(self):
        return self.screen.extension

    @extension.setter
    def extension(self, extension):
        self.screen.extension = extension

    @property
    def minVal(self):
        return self.screen.minVal

    @minVal.setter
    def minVal(self, minVal):
        self.screen.minVal = minVal

    @property
    def maxVal(self):
        return self.screen.maxVal

    @maxVal.setter
    def maxVal(self, maxVal):
        self.screen.maxVal = maxVal

class FrictionGlider(wx.Window):
    def __init__(self, parent, eventHandler=None, **kwargs):
        if not 'style' in kwargs:
            kwargs['style'] = 0
        kwargs['style'] |= wx.BORDER_SIMPLE
        
        wx.Window.__init__(self, parent, **kwargs)

        self.eventHandler = eventHandler

        slider = wx.Slider(self)
        slider.SetMin(0)
        slider.SetMax(40)
        
        text = wx.StaticText(self, label="Friction", style=wx.ALIGN_CENTRE_HORIZONTAL)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(slider)
        sizer.Add(text, 1, wx.EXPAND)

        self.SetSizer(sizer)
        self.Layout()

        self.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnter)
        self.Bind(wx.EVT_SLIDER, self.OnSlider)

    def OnSlider(self, e):
        frictionCoefficient = e.GetInt() * 1. / 20 
        event = FrictionUpdateEvent(value=frictionCoefficient)
        wx.PostEvent(self.eventHandler, event)

    def OnMouseEnter(self, e):
        self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
        for child in self.GetChildren():
            child.SetCursor(wx.Cursor(wx.CURSOR_ARROW))

if __name__ == '__main__':
    app = wx.App(False)
    frame = wx.Frame(None)
    window = wx.Window(frame, size=wx.Size(500, 400))
    ed = EnergyDisplay(window, size=wx.Size(400, 400))
    #fg = FrictionGlider(frame, size=(200, 200))
    frame.Show(True)
    app.MainLoop()