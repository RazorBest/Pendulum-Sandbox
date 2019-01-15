from sympy import symbols, Dummy, lambdify
from sympy.physics.mechanics import *
from numpy import array, hstack, zeros, linspace, pi, ones
from numpy.linalg import solve
from scipy.integrate import odeint
import matplotlib.pyplot as plt

class Pendulum:

    def __init__(self):
        self.id = 0

        self.N = ReferenceFrame('N')  # The inertial reference frame
        self.O = Point('O')           # The origin point    
        self.O.set_vel(self.N, 0)
        self.g = symbols('g')
        #self.t = symbols('t')

        self.kd = []
        self.FL = []
        self.BL = []
        self.angles = []
        self.velocities = []
        self.points = [self.O]
        #self.masses = []
        self.parameters = [self.g]
        self.parameter_vals = [9.81, 1, 1]

        self.KM = None
        self.kdd = None
        self.mm = None
        self.fo = None
        self.M_func = None
        self.F_func = None
        self.dynamic = None

    def AddPendulum(self):
        self.id += 1
        id_s = str(self.id)
        N = self.N
        O = self.O
        g = self.g

        q = dynamicsymbols('q' + id_s)
        qd = dynamicsymbols('q' + id_s, 1)
        u = dynamicsymbols('u' + id_s)
        ud = dynamicsymbols('u' + id_s, 1)
        l, m = symbols('l' + id_s + ' ' + 'm' + id_s)
        self.parameters += [l, m]

        A = N.orientnew('A' + id_s, 'Axis', [q, N.z])
        A.set_ang_vel(N, u * N.z)
        P = O.locatenew('P' + id_s, l * A.x)    
        P.v2pt_theory(self.points[len(self.points) - 1], N, A)
        Par = Particle('Par' + id_s, P, m)

        self.angles.append(q)
        self.velocities.append(u)
        self.points.append(P)
        self.kd.append(qd - u)
        self.FL.append((P, m * g * N.x))
        self.BL.append(Par)

        self.KM = KanesMethod(N, q_ind=self.angles, u_ind=self.velocities, kd_eqs=self.kd)
        (fr, frstar) = self.KM.kanes_equations(self.BL, self.FL)
        self.kdd = self.KM.kindiffdict()
        self.mm = self.KM.mass_matrix_full
        self.fo = self.KM.forcing_full
        qudots = self.mm.inv() * self.fo
        qudots = qudots.subs(self.kdd)
        qudots.simplify()
        mechanics_printing()
        #mprint(fr)
        #mprint(qudots)
    
    def SetParameters(self):
        dynamic = self.angles + self.velocities
        self.dynamic = dynamic
        dummy_symbols = [Dummy() for i in dynamic]
        dummy_dict = dict(zip(dynamic, dummy_symbols))
        M = self.mm.subs(self.kdd).subs(dummy_dict)
        F = self.fo.subs(self.kdd).subs(dummy_dict)
        print self.mm
        print self.fo
        print self.mm.subs(self.kdd)
        print self.fo.subs(self.kdd)
        print M
        print F
        print dummy_dict
        self.M_func = lambdify(dummy_symbols + self.parameters, M)
        self.F_func = lambdify(dummy_symbols + self.parameters, F)

    def OutputGraph(self):
        x0 = hstack((0, pi / 2 * ones(len(self.angles) - 1), 1e-3 * ones(len(self.velocities))))
        t = linspace(0, 10, 1000)
        y = odeint(self.right_hand_side, x0, t, args=(self.parameter_vals,))
        lines = plt.plot(t, y[:, :y.shape[1] / 2])
        lab = plt.xlabel('Time [sec]')
        leg = plt.legend(self.dynamic[:y.shape[1] / 2])

    def right_hand_side(self, x, t, args):
        u = 0.0
        arguments = hstack((x, u, args))
        dx = array(solve(self.M_func(*arguments), self.F_func(*arguments))).T[0]

        return dx

if __name__ == '__main__':
    p = Pendulum()
    p.AddPendulum()
    #p.AddPendulum()
    p.SetParameters()
    p.OutputGraph()
