"""
    This is a simulation of an n-link pendulum
"""
import os
import time
import threading
import wx
import wx.lib.resizewidget
import wx.lib.agw.customtreectrl
from pendulum import Pendulum

class BufferedWindow(wx.Window):
    def __init__(self, *args, **kwargs):
        kwargs['style'] = kwargs.setdefault('style', wx.NO_FULL_REPAINT_ON_RESIZE) | wx.NO_FULL_REPAINT_ON_RESIZE
        wx.Window.__init__(self, *args, **kwargs)

        # Setting up the event handlers
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)

        #self.OnSize(None)

    # This funtion is for subclasses
    def Draw(self, dc):
        pass

    def UpdateDrawing(self, rect=None):
        dc = wx.MemoryDC()
        dc.SelectObject(self._Buffer)
        self.Draw(dc)
        del dc
        #self.Refresh(eraseBackground=False, rect=rect)
        #self.Update()
        wx.CallAfter(self.Paint)
        #self.Draw(wx.BufferedDC(wx.ClientDC(self), self._Buffer))

        #self.Layout()

    def OnSize(self, e=None):
        size = self.GetClientSize()
        #size = self.GetParent().GetSize()
        self._Buffer = wx.Bitmap(size)
        self.UpdateDrawing()
        if e != None:
            e.Skip()

    def OnPaint(self, e=None):
        self.Draw(wx.BufferedPaintDC(self, self._Buffer))
        #e.Skip()

    #does the same thing as OnPaint but is called by the client, not from a PaintEvent handler
    def Paint(self):
        self.Draw(wx.BufferedDC(wx.ClientDC(self), self._Buffer))

class SimulationWindow(BufferedWindow):
    main_thread = None

    def __init__(self, *args, **kwargs):
        self.ticksPerSecond = 500
        self.pendulum = Pendulum(200, 100, 1. / self.ticksPerSecond)
        self.pendulum.AddPendulum(20, 80, 2, 0)
        self.pendulum.AddPendulum(20, 180, 1.5, 0)

        #kwargs['size'] = (300, 200)
        BufferedWindow.__init__(self, *args, **kwargs)

        self.running = False
        self.SetBackgroundColour(wx.WHITE)

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
        self.pause = False

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
        self.pendulum.Tick()

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

        self.pendulum.Draw(dc)

    def SetPause(self, pause):
        self.pause = pause

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

class VariableEditor(wx.CollapsiblePane):
    def __init__(self, *args, **kwargs):
        wx.CollapsiblePane.__init__(self, *args, **kwargs)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.GetPane().SetSizer(self.sizer)

    def AddVariable(self, variableName=None):
        t = wx.TextCtrl(self.GetPane(), id=wx.ID_ANY, style=wx.BORDER_DEFAULT)
        t.ShowNativeCaret()
        if len(self.sizer.GetChildren()) > 0: #If this is not the first inserted textbox
           self.sizer.AddSpacer(15)
        self.sizer.Add(t, flag=wx.LEFT|wx.RIGHT, border=10)

        self.sizer.Layout()

class Explorer(wx.Panel):
    def __init__(self, *args, **kwargs):
        wx.Window.__init__(self, *args, **kwargs)

        textCtrl = []
        self.horizontalSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.verticalSizer = wx.BoxSizer(wx.VERTICAL)

        button = wx.Button(self, label='+Add Pendulum')
        button.SetFont(wx.Font(13, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        pane = VariableEditor(self)

        self.verticalSizer.Add(button)
        self.verticalSizer.Add(pane, 0)

        for i in range(6):
            pane.AddVariable()

        self.horizontalSizer.Add(self.verticalSizer, proportion=1, flag=wx.EXPAND|wx.RIGHT, border=10)
        self.SetSizer(self.horizontalSizer)

        self.Bind(wx.EVT_MOTION, self.OnMouseMove)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnMousePress)
        self.Bind(wx.EVT_LEFT_UP, self.OnMouseRelease)
        self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.OnMouseCaptureLost)

        self.sizing = False

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

    def OnMouseCaptureLost(self, e):
        self.ReleaseMouse()

class FillWindow(wx.Window):
    def __init__(self, *args, **kwargs):
        wx.Window.__init__(self, *args, **kwargs)

        #self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnErase)
        self.Bind(wx.EVT_MOTION, self.OnMouse)

    def ChangeCursor(self, stockCursor):
        self.SetCursor(wx.Cursor(stockCursor))
        if stockCursor == wx.CURSOR_ARROW:
            self.GetParent().movingState = False
        elif stockCursor == wx.CURSOR_SIZING:
            self.GetParent().movingState = True

    def OnErase(self, e):
        pass

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

        #self.control = wx.TextCtrl(self, style=wx.TE_MULTILINE)
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
        toolbar.Realize()


        # Set events
        self.Bind(wx.EVT_MENU, self.OnOpen, menuOpen)
        self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
        self.Bind(wx.EVT_MENU, self.OnExit, menuExit)
        self.Bind(wx.EVT_TOOL, self.OnChangeCursor, self.selectionTool)
        self.Bind(wx.EVT_TOOL, self.OnChangeCursor, self.moveTool)
        self.Bind(wx.EVT_TOOL, self.OnTogglePlay, self.playTool)
        self.Bind(wx.EVT_TOOL, self.OnTogglePlay, self.pauseTool)

        self.window = SimulationWindow(self, size=(width, height))
        self.fillWindow = FillWindow(self.window, style=wx.TRANSPARENT_WINDOW)

        explorerPanel = Explorer(self.window, size=(150, height), style=wx.BORDER_SIMPLE)
        explorerPanel.SetBackgroundColour(wx.Colour(200, 200, 200))
        #treectrl = wx.TreeCtrl(self.window)
        #root = treectrl.AddRoot('Adsa')
        #treectrl.AppendItem(root, 'adsa1')
        #treectrl.AppendItem(root, 'adsa2')
        #treectrl.AppendItem(root, 'adsa3')
        windowSizer = wx.BoxSizer(wx.HORIZONTAL)
        #explorerPanel.SetSize(150, height)
        windowSizer.Add(explorerPanel)

        windowSizer.Add(self.fillWindow, 1, wx.EXPAND)
        #flagsExpand = wx.SierFlags(1)
        #windowSizer.Add(self.fillWindow, wx.EXPAND)
        self.window.SetSizer(windowSizer)

        #window.SetPosition((0, 0))
        #explorerPanel = wx.Panel(self, size=(200,200))

        #sizer = wx.BoxSizer(wx.HORIZONTAL)
        #sizer.Add(explorerPanel, 0)
        #sizer.Add(window)
        #self.SetSizer(sizer)
        #self.SetAutoLayout(True)
        #sizer.Fit(window)

        self.Centre()
        self.Show(True)

    """def UpdateDrawing(self): old thing
        dc = wx.MemoryDC()
        dc.SelectObject(self._Buffer)
        self.Draw(dc)
        del dc
        self.Refresh(eraseBackground=False)
        self.Update()"""

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
