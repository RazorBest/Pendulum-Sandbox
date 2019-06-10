from math import sin, cos

class EnergyExtension():
    def __init__(self, pendulum):
        self.pendulum = pendulum
        objects = self.pendulum.GetVariableObjects()
        self.angles = objects['angles']
        self.velocities = objects['velocities']
        self.masses = objects['masses']
        self.lengths = objects['lengths']
        self.g = objects['g']
    
    def GetPotentialEnergy(self):
        energy = 0
        n = len(self.masses)
        # Suppose the pivot has coordinates (0, 0)
        y = 0
        total_length = 0
        for i in range(n):
            y += cos(self.angles[i]) * self.lengths[i]
            total_length += self.lengths[i]
            energy += self.masses[i] * self.g * (total_length - y)

        return energy

    def GetKineticEnergy(self):
        energy = 0
        n = len(self.masses)
        vx = 0
        vy = 0
        for i in range(n):
            vx += self.lengths[i] * self.velocities[i] * cos(self.angles[i])
            vy += self.lengths[i] * self.velocities[i] * sin(self.angles[i])
            energy += self.masses[i] * (vx * vx + vy * vy) * 1. / 2

        return energy

if __name__ == '__main__':
    from pendulum import PendulumBase

    pendulum = PendulumBase(1, 1, 0.0001)
    pendulum.AddBob(1, angle=3, mass=1, length=100)
    pendulum.AddBob(2, angle=3.1415, mass=1, length=100)
    pendulum.AddBob(3, length=100, angle=3.1415, mass=1)
    ee = EnergyExtension(pendulum)
    variables = pendulum.GetVariableObjects()

    mini = ee.GetPotentialEnergy() + ee.GetKineticEnergy()
    maxi = mini
    
    print "Init total: " + str(mini)

    for i in range(0, 30000):
        pendulum.Tick()
        total = ee.GetPotentialEnergy() + ee.GetKineticEnergy()
        mini = min(mini, total)
        maxi = max(maxi, total)

    print "Current total: " + str(ee.GetPotentialEnergy() + ee.GetKineticEnergy())
    print "Min: " + str(mini)
    print "Max: " + str(maxi)
    print variables
