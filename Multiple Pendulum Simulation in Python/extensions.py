import wx
import pendulum

class EnergyExtension():
    def __init__(self, pendulum):
        self.pendulum = pendulum

        objects = self.pendulum.GetVariableObjects()
    
    def GetPotentialEnergy(self):
        return self.pendulum.GetVariableObjects()

if __name__ == '__main__':
    pendulum = pendulum.PendulumBase(1, 1, 0.01)
    pendulum.AddBob(1, angle=1)
    pendulum.AddBob(2, angle=2)
    pendulum.AddBob(3, length=50, angle=3)
    ee = EnergyExtension(pendulum)
    variables = ee.GetPotentialEnergy()
    pendulum.AddBob(2, angle=2)
    pendulum.AddBob(3, length=50, angle=3)

    for i in range(0, 1000):
        pendulum.Tick()
        print variables
        x = raw_input()

