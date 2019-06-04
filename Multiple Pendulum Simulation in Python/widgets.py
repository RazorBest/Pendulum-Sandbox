import wx
import wx.lib.newevent
from main import BufferedWindow

FrictionUpdateEvent, EVT_FRICTION_UPDATE = wx.lib.newevent.NewEvent()

class EnergyDisplay(BufferedWindow):
    def __init__(self, *args, **kwargs):
        BufferedWindow.__init__(self, *args, **kwargs)

        self.SetBackgroundColour(wx.Colour(wx.RED))

        self.minVal = 0
        self.maxVal = 10
        
        self.gridWidth = 10

        self.x = 10

        self.x_data = [0]
        self.y_data = [0]
        #xy_data = list(zip(self.x_data, self.y_data))

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.OnTimer, self.timer)
        self.timer.Start(1000) #calls OnTimer() every second

        #self.Bind(wx.EVT_SIZE, self.OnSize)

    def OnTimer(self, e):
        self.x_data.append(self.x * 30)
        
        self.y_data.append((self.x * 17) % 10)
        if (len(self.x_data) > 10):
            self.x_data.pop(0)
            self.y_data.pop(0)
        self.x += 1

        xy_data = list(zip(self.x_data, self.y_data))

        self.UpdateDrawing() #Should I use BufferedWindow?
    
    def Draw(self, dc):
        dc.SetPen(wx.Pen(wx.Colour(wx.BLACK)))
        dc.SetBrush(wx.Brush(wx.Colour(wx.BLACK)))
        dc.SetBackground(wx.Brush(wx.Colour(wx.WHITE)))

        dc.Clear()

        width, height = self.GetSize()

        firstX = self.x_data[0]
        firstY = self.y_data[0]
        lastX = firstX
        lastY = firstY
        for i in range(1, len(self.x_data)):
            y = self.y_data[i] - firstY
            x = i * width / self.gridWidth
            dc.DrawLine(lastX, lastY, x, y)
            lastX = x
            lastY = y

    def OnSize(self, e):
        pass

    def AddValue(self, value):
        self.values.append(value)

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