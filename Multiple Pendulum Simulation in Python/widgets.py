import wx
import wx.lib.newevent

FrictionUpdateEvent, EVT_FRICTION_UPDATE = wx.lib.newevent.NewEvent()

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

class GraphableData():
    def __init__(self, values=[], color=None, active=True):
        self.values = values
        self.color = color
        self.active = active
        self.iterator = 0

    @property
    def values(self):
        return self.__values

    @values.setter
    def values(self, values):
        self.__values = values

    @property
    def color(self):
        return self.__color

    @color.setter
    def color(self, color):
        self.__color = color

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

class UserResizableWindow(wx.Window):
    INVALID_POSITION = 0
    TOP_POSITION = 1
    BOTTOM_POSITION = 2
    RIGHT_POSITION = 4
    LEFT_POSITION = 8

    def __init__(self, parent, **kwargs):
        wx.Window.__init__(self, parent, **kwargs)

        self.resizableBarSpace = 15

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
        if mx <= self.resizableBarSpace:
            positionCode |= self.LEFT_POSITION
        elif mx >= width - self.resizableBarSpace:
            positionCode |= self.RIGHT_POSITION
        if my <= self.resizableBarSpace:
            positionCode |= self.TOP_POSITION
        elif my >= height - self.resizableBarSpace:
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

                if x > 2 * self.resizableBarSpace:
                    self.SetSize(x, height)

            if self.positionCode & self.BOTTOM_POSITION:
                x, y = e.x, e.y
                width, height = self.GetSize()

                if y > 2 * self.resizableBarSpace:
                    self.SetSize(width, y)

            if self.positionCode & self.LEFT_POSITION:
                x, y = self.ClientToScreen(e.x, e.y)
                parent = self.GetParent()
                x, y = parent.ScreenToClient(x, y)
                width, height = self.GetSize()
                posX, posY = self.GetPosition()

                if e.x < width - 2 * self.resizableBarSpace:
                    self.SetPosition((x, posY))
                    self.SetSize(width + posX - x, height)

            if self.positionCode & self.TOP_POSITION:
                x, y = self.ClientToScreen(e.x, e.y)
                parent = self.GetParent()
                x, y = parent.ScreenToClient(x, y)
                width, height = self.GetSize()
                posX, posY = self.GetPosition()

                if e.y < height - 2 * self.resizableBarSpace:
                    self.SetPosition((posX, y))
                    self.SetSize(width, height + posY - y)


    def OnMousePress(self, e):
        if self.positionCode != self.INVALID_POSITION:
            self.sizing = True
            self.CaptureMouse()
        
    def OnMouseRelease(self, e):
        self.sizing = False
        self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
        #self.GetContainingSizer().SetItemMinSize(self, self.GetRect().width, self.GetRect().height)
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

class EnergyDisplay(LiveObject, UserResizableWindow):
    def __init__(self, parent, ticksPerUpdate=1, scale=10, extension=None, **kwargs):
        #wx.Window.__init__(self, parent, **kwargs)
        LiveObject.__init__(self, ticksPerUpdate)
        UserResizableWindow.__init__(self, parent, **kwargs)

        self._extension = extension
        self.scale = scale

        self.minVal = 0
        self.maxVal = 10
        self.markerCount = 5

        self.originX = 50
        self.originY = 30

        self.data = {"potential":GraphableData([0], wx.Colour(wx.BLUE)), 
                    "kinetic":GraphableData([0], wx.Colour(wx.RED)), 
                    "total":GraphableData([0], wx.Colour(wx.BLACK))
                    }
        self.dataIterator = 1

        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        
        self.clear = True

    def UpdateData(self):
        potential = self._extension.GetPotentialEnergy()
        kinetic = self._extension.GetKineticEnergy()
        total = potential + kinetic
        self.AddValue('potential', potential)
        self.AddValue('kinetic', kinetic)
        self.AddValue('total', total)

        width, height = self.GetSize()
        n = len(self.data['potential'].values)
        while self.scale * (n + 3) > width:
            self.clear = True
            for data in self.data.values():
                data.values.pop(0)
            n = len(self.data['potential'].values)

        #self.Refresh()
        #Update the paint
        dc = wx.ClientDC(self)
        self.Draw(dc)

    def DrawMarkers(self, dc):
        width, height = self.GetSize()

        y = self.originY
        unit = (height - self.originY) * 1. / self.markerCount

        dc.DrawRectangle(0, 0, width, 10)
        dc.DrawLine(self.originX, height, self.originX, 0)

        while y < height:
            value = (y - self.originY) * 1. / (height - self.originY) * (self.maxVal - self.minVal) + self.minVal
            dc.DrawText("%.1f" % (value) + " J", 0, height - y)
            dc.DrawLine(self.originX - 10, height - y, self.originX + 10, height - y)
            y += unit

    def Draw(self, dc):
        dc.SetPen(wx.Pen(wx.Colour(wx.BLACK)))
        dc.SetBrush(wx.Brush(wx.Colour(wx.BLACK)))
        
        if self.clear:
            dc.SetBackground(wx.Brush(wx.Colour(wx.WHITE)))
            dc.Clear()
            #redraws all the lines between the points
            self.dataIterator = 1
            self.clear = False

            self.DrawMarkers(dc)

        width, height = self.GetSize()
        interval = self.maxVal - self.minVal

        i = None
        for data in self.data.values():
            
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

        self.dataIterator = i

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
        self.data[key].values.append(value)
        if (value + 20 > self.maxVal):
            self.maxVal = value + 20
            self.clear = True
        if value < self.minVal:
            self.minVal = value
            self.clear = True
    
    @property
    def extension(self):
        return self._extension

    @extension.setter
    def extension(self, extension):
        self._extension = extension

    def SetMinVal(self, minVal):
        self.minVal = minVal

    def SetMaxVal(self, maxVal):
        self.maxVal = maxVal

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