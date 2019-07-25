import wx

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
