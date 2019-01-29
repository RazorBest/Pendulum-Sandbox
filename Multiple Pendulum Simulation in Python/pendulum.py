from __future__ import division
from numpy.linalg import det, solve
from numpy import zeros, float64
from math import sin, cos
from array import array
import wx
import time

class Pendulum:

    def __init__(self, x, y, timeInterval):
        self.x = x
        self.y = y

        self.id = 0

        self.g = 9.8
        self.n = 0
        self.angles = [0]
        self.vels = []
        self.m = []
        self.l = []
        self.deltaT = timeInterval
        self.scale = 100

    def InitArrays(self):
        n = self.n
        self.A = zeros((2 * n , 2 * n), dtype=float64)
        self.B = zeros(2 * n, dtype=float64)
        self.lc = zeros(n, dtype=float64)
        self.ls = zeros(n, dtype=float64)
        self.lcv = zeros(n, dtype=float64)
        self.lsv = zeros(n, dtype=float64)

    def AddPendulum(self, mass, length, angle, velocity):
        self.id += 1
        id_s = str(self.id)
        
        self.m.append(mass)
        self.l.append(length / self.scale)
        self.vels.append(velocity)
        self.angles.insert(self.n, angle)
        self.n += 1

        self.InitArrays()
    
    def Accelerations(self):
        n = self.n
        a = self.angles
        
        for i in range(0, n):
            self.lc[i] = self.l[i] * cos(a[i])
            self.ls[i] = self.l[i] * sin(a[i])
            self.lcv[i] = self.lc[i] * self.vels[i] * self.vels[i]
            self.lsv[i] = self.ls[i] * self.vels[i] * self.vels[i]
        for i in range(0, n):
            for j in range(0, i + 1):
                self.A[2 * i][j] = - self.lc[j]#self.l[j] * cos(a[j])#
                self.A[2 * i + 1][j] = - self.ls[j]#self.l[j] * sin(a[j])#
                #B[2 * i] += - lsv[j]#self.l[j] * sin(a[j]) * self.vels[j] * self.vels[j]#
                #B[2 * i + 1] += lcv[j]#self.l[j] * cos(a[j]) * self.vels[j] * self.vels[j]
            
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
        for i in range(0, self.n):
            self.vels[i] += acc[i] * self.deltaT
            self.angles[i] += self.vels[i] * self.deltaT
        
    def Draw(self, dc, tx=0, ty=0):
        x = self.x
        y = self.y

        dc.SetBrush(wx.Brush(wx.BLACK))
        dc.SetPen(wx.Pen(wx.BLACK))
        nx = x + sin(self.angles[0]) * self.l[0] * self.scale
        ny = y + cos(self.angles[0]) * self.l[0] * self.scale
        dc.DrawLine(x, y, nx, ny)
        dc.DrawCircle(x, y, 10)
        for i in range(1, self.n):
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
    p.AddPendulum(20, 81, 1, 0)
    p.AddPendulum(20, 100, 1, 0)
    p.AddPendulum(29, 120, 1.5, 0)
    p.AddPendulum(30, 120, 1.5, 0)
    p.AddPendulum(15, 50, 0.5, 0)
    ticks = 200000
    t = time.clock()
    for i in range(0, ticks):
        p.Tick()
    t = time.clock() - t
    print 'Time: ' + str(t)
    f = open('pendulum_performance_time.txt', 'a')
    f.write('n=' + str(p.n) + '\n')
    f.write('ticks=' + str(ticks) + '\n')
    f.write('time=' + str(t) + '\n')
    f.write('\n')
    f.close()
