from __future__ import division
import numpy
from numpy.linalg import solve
from numpy import zeros, float64
from math import sin, cos, sqrt
import wx
import time
from updatable import Updatable

numpy.seterr(all='raise')

class PendulumBase(Updatable):

    frictionCoefficient = 0

    def __init__(self, x, y, timeInterval):
        Updatable.__init__(self, updateInterval=timeInterval)

        self.x = x
        self.y = y

        self.bobCount = 0

        self.g = 9.8
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

    def InsertBob(self, bobId, pos=-1, mass=10, length=100, angle=0, velocity=0):
        #Here I should raise an exception if the bobId is already used
        
        if pos == -1:
            pos = self.bobCount
        
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
        if self.bobCount == 0:
            return

        n = self.bobCount
        a = self.angles

        #Check boundaries
        for i in range(0, n):
            if self.vels[i] < -100:
                self.vels[i] = 100
            if self.vels[i] > 100:
                self.vels[i] = 100

        for i in range(0, n):
            self.lc[i] = self.l[i] * cos(a[i])
            self.ls[i] = self.l[i] * sin(a[i])
            self.lcv[i] = self.lc[i] * self.vels[i] * self.vels[i]
            self.lsv[i] = self.ls[i] * self.vels[i] * self.vels[i]
        for i in range(0, n):
            for j in range(0, i + 1):
                self.A[2 * i][j] = - self.lc[j]
                self.A[2 * i + 1][j] = - self.ls[j]

            frictionX = abs(self.vels[i]) * self.frictionCoefficient * cos(a[i])
            frictionY = abs(self.vels[i]) * self.frictionCoefficient * sin(a[i])

            if self.vels[i] < 0:
                frictionX *= -1
                frictionY *= -1

            self.B[2 * i] = - self.lsv[i] + frictionX
            self.B[2 * i + 1] = self.lcv[i] + frictionY

            if i > 0:
                self.B[2 * i] += self.B[2 * i - 2]
                self.B[2 * i + 1] += self.B[2 * i - 1]
            else:
                self.B[2 * i + 1] += self.g
            self.A[2 * i][n + i] = - sin(a[i]) / self.m[i]
            self.A[2 * i + 1][n + i] = cos(a[i]) / self.m[i]
            if i == n - 1:
                continue
            self.A[2 * i][n + i + 1] = sin(a[i + 1]) / self.m[i]
            self.A[2 * i + 1][n + i + 1] = - cos(a[i + 1]) / self.m[i]

        assert(not numpy.isnan(self.A).any() and not numpy.isnan(self.B).any()), "There are NaN values in the arrays - pendulum.py Accelerations()"


        acc = solve(self.A, self.B)
        return acc[:n]

    def UpdateData(self):
        acc = self.Accelerations()
        for i in range(0, self.bobCount):
            self.vels[i] += acc[i] * self.deltaT
            self.angles[i] += self.vels[i] * self.deltaT

    def GetX(self):
        return self.x

    def SetX(self, x):
        self.x = x

    def GetY(self):
        return self.y

    def SetY(self, y):
        self.y = y

    def GetVariableObjects(self):
        return {
            "angles": self.angles, 
            "velocities": self.vels,
            "masses": self.m,
            "lengths": self.l,
            "g": self.g}
    
    @property
    def timeInterval(self):
        return self.deltaT
    
    @timeInterval.setter
    def timeInterval(self, timeInterval):
        self.deltaT = timeInterval

class CollisionState():
    def __init__(self, pivot=False, bobIndex=0, lastBob=False, rod=False, id=0):
        self.pivot = pivot
        self.bobIndex = bobIndex
        self.lastBob = lastBob
        self.rod = rod
        self.id = id

class Pendulum(PendulumBase):
    radius = 13

    def __init__(self, x, y, timeInterval):
        PendulumBase.__init__(self, x, y, timeInterval)

        self.selected = False
        self.hovered = False

    def GetPivot(self):
        return self.x, self.y

    def GetPos(self, bobId=None):
        index = self.bobCount
        if bobId != None:
            index = self.idList.index(bobId)
        x = self.x
        y = self.y
        for i in range(index):
            x += sin(self.angles[i]) * self.l[i] * self.scale
            y += cos(self.angles[i]) * self.l[i] * self.scale
        return (x, y)

    def PendulumCollision(self, mx, my):
        """Check if the cursor at the coordinates (mx, my) is over the pendulum
                (over any bob or its rods)
        """

        x = self.x
        y = self.y

        # Check collision for the pivot
        if self.BobCollision(mx, my, x, y, self.radius):
            if self.bobCount == 0:
                return CollisionState(pivot=True, lastBob=True)
            return CollisionState(pivot=True)

        for i in range(0, self.bobCount):
            nx = x + sin(self.angles[i]) * self.l[i] * self.scale
            ny = y + cos(self.angles[i]) * self.l[i] * self.scale

            if self.BobCollision(mx, my, nx, ny, self.radius):
                # If it is the last bob
                if i == self.bobCount - 1:
                    return CollisionState(bobIndex=self.idList[i], lastBob=True)
                return CollisionState(bobIndex=self.idList[i])

            if self.RodCollision(mx, my, x, y, nx, ny, 5):
                return CollisionState(rod=True)

            x = nx
            y = ny

        # Return default state if no collision happens
        return CollisionState()

    def Distance(self, x1, y1, x2, y2):
        return sqrt((x1 - x2)**2 + (y1 - y2)**2)

    def BobCollision(self, mx, my, x, y, r):
        return self.Distance(mx, my, x, y) <= r

    def RodCollision(self, mx, my, x1, y1, x2, y2, l):
        p = self.GetRect(x1, y1, x2, y2, l)

        ans = False
        i = 0
        j = 3
        while i < 4:
            if ((p[i][1]>my) != (p[j][1]>my)) and (mx < (p[j][0]-p[i][0]) * (my-p[i][1]) / (p[j][1]-p[i][1]) + p[i][0]):
                ans = not ans
            j = i
            i += 1

        return ans

    def GetRect(self, x1, y1, x2, y2, l):
        dx = 0
        if y1 != y2:
            dx = l / sqrt(1 + (x2 - x1)**2 / ((y2 - y1)**2))
            if (x2 - x1)*(y2 - y1) < 0:
                dx = -dx
        dy = 0
        if x1 != x2:
            dy = l / sqrt(1 + (y2 - y1)**2 / ((x2 - x1)**2))
            if (x2 - x1)*(y1 - y1) < 0:
                dy = -dy
        p = 4*[(0, 0)]
        p[0] = (x1 - dx, y1 + dy)
        p[1] = (x2 - dx, y2 + dy)
        p[2] = (x2 + dx, y2 - dy)
        p[3] = (x1 + dx, y1 - dy)

        return p

    def Draw(self, dc, tx=0, ty=0):
        x = self.x
        y = self.y

        if self.bobCount == 0:
            if self.selected:
                dc.SetBrush(wx.Brush(wx.Colour(186, 170, 221)))
                dc.SetPen(wx.Pen(wx.Colour(186, 170, 221)))
                dc.DrawCircle(x, y, self.radius)
            dc.SetBrush(wx.Brush(wx.BLACK))
            dc.SetPen(wx.Pen(wx.BLACK))
            dc.DrawCircle(x, y, self.radius - 3)
            return

        nx = x + sin(self.angles[0]) * self.l[0] * self.scale
        ny = y + cos(self.angles[0]) * self.l[0] * self.scale
        if self.selected:
            dc.SetBrush(wx.Brush(wx.Colour(186, 170, 221)))
            dc.SetPen(wx.Pen(wx.Colour(186, 170, 221)))

            dc.DrawCircle(x, y, self.radius)
            points = self.GetRect(x, y, nx, ny, 2)
            dc.DrawPolygon(points)

        dc.SetBrush(wx.Brush(wx.BLACK))
        dc.SetPen(wx.Pen(wx.BLACK))
        try:
            dc.DrawLine(x, y, nx, ny)
        except:
            print "ERROR in pendulum.py Draw(): " + "x = " + str(x) + "\ny = " + str(y)
            print "nx = " + str(nx) + "\nny = " + str(ny)
            return
        dc.DrawCircle(x, y, self.radius - 3)

        for i in range(1, self.bobCount):

            if self.selected:
                dc.SetBrush(wx.Brush(wx.Colour(186, 170, 221)))
                dc.SetPen(wx.Pen(wx.Colour(186, 170, 221)))

                dc.DrawCircle(nx, ny, self.radius + 4)
                points = self.GetRect(
                    nx + tx,
                    ny + ty,
                    nx + sin(self.angles[i]) * self.l[i] * self.scale + tx,
                    ny + cos(self.angles[i]) * self.l[i] * self.scale + ty,
                    3)
                dc.DrawPolygon(points)

            dc.SetBrush(wx.Brush(wx.BLACK))
            dc.SetPen(wx.Pen(wx.BLACK))
            dc.DrawLine(
                nx + tx,
                ny + ty,
                nx + sin(self.angles[i]) * self.l[i] * self.scale + tx,
                ny + cos(self.angles[i]) * self.l[i] * self.scale + ty)

            dc.SetBrush(wx.Brush(wx.Colour(68, 68, 68)))
            dc.SetPen(wx.Pen(wx.Colour(68, 68, 68)))
            dc.DrawCircle(nx, ny, self.radius)
            x = nx
            y = ny
            nx += sin(self.angles[i]) * self.l[i] * self.scale
            ny += cos(self.angles[i]) * self.l[i] * self.scale

        if self.selected:
            dc.SetBrush(wx.Brush(wx.Colour(186, 170, 221)))
            dc.SetPen(wx.Pen(wx.Colour(186, 170, 221)))
            dc.DrawCircle(nx, ny, self.radius + 4)

        dc.SetBrush(wx.Brush(wx.Colour(68, 68, 68)))
        dc.SetPen(wx.Pen(wx.Colour(68, 68, 68)))
        dc.DrawCircle(nx, ny, self.radius)

    def SetSelected(self, selected=True):
        self.selected = selected

    def IsSelected(self):
        return self.selected

    def SetHovered(self, hovered=True):
        self.hover = hover

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
        p.UpdateData()
    t = time.clock() - t
    print 'Time: ' + str(t)
    f = open('pendulum_performance_time.txt', 'a')
    f.write('n=' + str(p.bobCount) + '\n')
    f.write('ticks=' + str(ticks) + '\n')
    f.write('time=' + str(t) + '\n')
    f.write('\n')
    f.close()
