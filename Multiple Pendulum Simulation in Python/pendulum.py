from __future__ import division
from numpy.linalg import solve
from numpy import zeros, float64
from math import sin, cos
#from array import array
import wx
import time

class Pendulum():

    def __init__(self, x, y, timeInterval):
        self.x = x
        self.y = y

        self.bobCount = 0

        self.g = 9.8
        #self.n = 0
        self.angles = [0]
        self.vels = []
        self.m = []
        self.l = []
        self.deltaT = timeInterval
        self.scale = 100

        self.A = None
        self.B = None
        self.lc = None
        self.ls = None
        self.lcv = None
        self.lsv = None

        self.idList = []

    def InitArrays(self):
        n = self.bobCount
        self.A = zeros((2 * n , 2 * n), dtype=float64)
        self.B = zeros(2 * n, dtype=float64)
        self.lc = zeros(n, dtype=float64)
        self.ls = zeros(n, dtype=float64)
        self.lcv = zeros(n, dtype=float64)
        self.lsv = zeros(n, dtype=float64)

    def InsertBob(self, bobId, pos, mass=10, length=100, angle=0, velocity=0):
        self.bobCount += 1
        self.idList.insert(pos, bobId)

        self.m.insert(pos, mass)
        self.l.insert(pos, length / self.scale)
        self.vels.insert(pos, velocity)
        self.angles.insert(pos, angle)

        self.InitArrays()

    def AddBob(self, bobId, mass=10, length=100, angle=0, velocity=0):
        self.InsertBob(bobId, self.bobCount, mass, length, angle, velocity)
    
    def RemoveBob(self, bobId):
        self.bobCount -= 1
        index = self.idList.index(bobId)
        self.idList.pop(index)

        self.m.pop(index)
        self.l.pop(index)
        self.vels.pop(index)
        self.angles.pop(index)
        
        self.InitArrays()

    def SetBob(self, bobId, mass=None, length=None, angle=None, velocity=None):
        index = self.idList.index(bobId)
        if mass != None:
            self.m[index] = mass
        if length != None:
            self.l[index] = length / self.scale
        if angle != None:
            self.angles[index] = angle
        if velocity != None:
            self.vels[index] = velocity

    def Accelerations(self):
        n = self.bobCount
        a = self.angles

        for i in range(0, n):
            self.lc[i] = self.l[i] * cos(a[i])
            self.ls[i] = self.l[i] * sin(a[i])
            self.lcv[i] = self.lc[i] * self.vels[i] * self.vels[i]
            self.lsv[i] = self.ls[i] * self.vels[i] * self.vels[i]
        for i in range(0, n):
            for j in range(0, i + 1):
                self.A[2 * i][j] = - self.lc[j]
                self.A[2 * i + 1][j] = - self.ls[j]

            self.B[2 * i] = - self.lsv[i]
            self.B[2 * i + 1] = self.lcv[i]
            if i > 0:
                self.B[2 * i] += self.B[2 * i - 2]
                self.B[2 * i + 1] += self.B[2 * i - 1]
            else:
                self.B[2 * i + 1] += self.g
            self.A[2 * i][n + i] = - sin(a[i]) / self.m[i]
            self.A[2 * i + 1][n + i] = cos(a[i]) / self.m[i]
            #B[2 * i + 1] += self.g
            if i == n - 1:
                continue
            self.A[2 * i][n + i + 1] = sin(a[i + 1]) / self.m[i]
            self.A[2 * i + 1][n + i + 1] = - cos(a[i + 1]) / self.m[i]

        acc = solve(self.A, self.B)
        return acc[:n]

    def Tick(self):
        acc = self.Accelerations()
        for i in range(0, self.bobCount):
            self.vels[i] += acc[i] * self.deltaT
            self.angles[i] += self.vels[i] * self.deltaT

    def Draw(self, dc, tx=0, ty=0):
        if self.bobCount == 0:
            return
            
        x = self.x
        y = self.y

        dc.SetBrush(wx.Brush(wx.BLACK))
        dc.SetPen(wx.Pen(wx.BLACK))
        nx = x + sin(self.angles[0]) * self.l[0] * self.scale
        ny = y + cos(self.angles[0]) * self.l[0] * self.scale
        dc.DrawLine(x, y, nx, ny)
        dc.DrawCircle(x, y, 10)
        for i in range(1, self.bobCount):
            dc.SetBrush(wx.Brush(wx.BLACK))
            dc.SetPen(wx.Pen(wx.BLACK))
            dc.DrawLine(nx + tx, ny + ty, nx + sin(self.angles[i]) * self.l[i] * self.scale + tx, ny + cos(self.angles[i]) * self.l[i] * self.scale + ty)
            dc.SetBrush(wx.Brush(wx.Colour(68, 68, 68)))
            dc.SetPen(wx.Pen(wx.Colour(68, 68, 68)))
            dc.DrawCircle(nx, ny, 13)
            x = nx
            y = ny
            nx += sin(self.angles[i]) * self.l[i] * self.scale
            ny += cos(self.angles[i]) * self.l[i] * self.scale
        dc.SetBrush(wx.Brush(wx.Colour(68, 68, 68)))
        dc.SetPen(wx.Pen(wx.Colour(68, 68, 68)))
        dc.DrawCircle(nx, ny, 13)


if __name__ == '__main__':
    p = Pendulum(30, 30, 0.001)
    p.AddBob(20, 81, 1, 0)
    p.AddBob(20, 100, 1, 0)
    p.AddBob(29, 120, 1.5, 0)
    p.AddBob(30, 120, 1.5, 0)
    p.AddBob(15, 50, 0.5, 0)
    ticks = 200000
    t = time.clock()
    for i in range(0, ticks):
        p.Tick()
    t = time.clock() - t
    print 'Time: ' + str(t)
    f = open('pendulum_performance_time.txt', 'a')
    f.write('n=' + str(p.bobCount) + '\n')
    f.write('ticks=' + str(ticks) + '\n')
    f.write('time=' + str(t) + '\n')
    f.write('\n')
    f.close()
