import wx
import wx.lib.newevent
from buffered import BufferedWindow
import random

FrictionUpdateEvent, EVT_FRICTION_UPDATE = wx.lib.newevent.NewEvent()

class EnergyDisplay(BufferedWindow):
    def __init__(self, *args, **kwargs):
        BufferedWindow.__init__(self, *args, **kwargs)

        self.SetBackgroundColour(wx.Colour(wx.RED))

        self.minVal = 0
        self.maxVal = 10
        self.markerCount = 5
        
        self.scale = 50

        self.originX = 50
        self.originY = 30

        self.data = [0]
        self.dataIterator = 1

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.OnTimer, self.timer)
        self.timer.Start(4000) #calls OnTimer() every second

        self.Bind(wx.EVT_SIZE, self.OnSize)

        random.seed()
        self.clear = True

    def OnTimer(self, e):
        self.AddValue(random.randint(0, 30))

        self.UpdateDrawing()
    
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

        i = self.dataIterator

        width, height = self.GetSize()

        interval = self.maxVal - self.minVal
        lastY = self.data[i - 1] * 1. / interval * (height - self.originY) + self.originY
        lastX = (i - 1) * self.scale + self.originX
        
        while i < len(self.data):
            y = self.data[i] * 1. / interval * (height - self.originY) + self.originY
            x = i * self.scale + self.originX
            dc.DrawLine(lastX, height - lastY, x, height - y)
            lastX = x
            lastY = y
            i += 1

        self.dataIterator = i

    def OnSize(self, e):
        self.clear = True
        e.Skip()

    def AddValue(self, value):
        print value

        self.data.append(value)
        if (value + 20 > self.maxVal):
            self.maxVal = value + 20
            self.clear = True
        if value < self.minVal:
            self.minVal = value
            self.clear = True

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
    ed = EnergyDisplay(frame, size=wx.Size(400, 400))
    #fg = FrictionGlider(frame, size=(200, 200))
    frame.Show(True)
    app.MainLoop()