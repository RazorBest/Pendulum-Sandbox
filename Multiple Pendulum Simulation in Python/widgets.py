import wx
from wx.lib import plot as wxplot
import buffered

class EnergyDisplay(wx.Window):
    def __init__(self, *args, **kwargs):
        wx.Window.__init__(self, *args, **kwargs)

        self.SetBackgroundColour(wx.Colour(wx.RED))

        self.minVal = 0
        self.maxVal = 10

        self.x = 10
        self.values = [1, 2, 3, 4, 5, 6, 7, 10, 11, 12, 13, 14, 5]
        self.polCoefficients = []

        self.x_data = []
        self.y_data = []
        xy_data = list(zip(self.x_data, self.y_data))

        line = wxplot.PolySpline(
            xy_data,
            colour=wx.Colour(128, 128, 0),   # Color: olive
            width=3,
        )

        # create your graphics object
        graphics = wxplot.PlotGraphics([line])

        # create your canvas
        self.panel = wxplot.PlotCanvas(self, size=wx.Size(200, 200))

        # Edit panel-wide settings
        axes_pen = wx.Pen(wx.BLUE, 1, wx.PENSTYLE_LONG_DASH)
        self.panel.axesPen = axes_pen

        # draw the graphics object on the canvas
        self.panel.Draw(graphics)

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.OnTimer, self.timer)
        self.timer.Start(1000)

    def OnTimer(self, e):
        self.x_data.append(self.x * 30)
        
        self.y_data.append((self.x * 17) % 10)
        if (len(self.x_data) > 10):
            self.x_data.pop(0)
            self.y_data.pop(0)
        self.x += 1

        xy_data = list(zip(self.x_data, self.y_data))

        line = wxplot.PolySpline(
            xy_data,
            colour=wx.Colour(128, 128, 0),   # Color: olive
            width=2,
        )

        # create your graphics object
        graphics = wxplot.PlotGraphics([line])

        # Edit panel-wide settings
        axes_pen = wx.Pen(wx.BLUE, 1, wx.PENSTYLE_LONG_DASH)
        self.panel.axesPen = axes_pen

        # draw the graphics object on the canvas
        self.panel.Draw(graphics)

        #self.UpdateDrawing()

    def AddValue(self, value):
        self.values.append(value)

    def SetMinVal(self, minVal):
        self.minVal = minVal

    def SetMaxVal(self, maxVal):
        self.maxVal = maxVal

if __name__ == '__main__':
    app = wx.App(False)
    frame = wx.Frame(None)
    ed = EnergyDisplay(frame, size=wx.Size(200, 200))
    frame.Show(True)
    app.MainLoop()