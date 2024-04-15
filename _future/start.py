"""
camphew is a minimalist python package for teaching computer-controlled instrumentation

---
current features and compatibilities:
    + runs a Basler camera using the pypylon package
    + have basic user interactions based on the matplotlib widget features

---

TODO:
adjust start.py to work with config files


::author::
Sanli Faez, Utrecht University, s.faez@uu.nl
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
from pypylon import pylon

#class Cam:

class Gui:
    """
    single port interface with a few bottons from matplotlib widgets
    """
    ind = 0
    freqs = np.arange(2, 20, 3)
    t = np.arange(0.0, 1.0, 0.001)
    s = np.sin(2 * np.pi * 4 * t)

    def __init__(self):
        fig, ax = plt.subplots()
        plt.subplots_adjust(bottom=0.2)

        self.scope, = plt.plot(self.t, self.s, lw=2)
        axprev = plt.axes([0.7, 0.05, 0.1, 0.075])
        axnext = plt.axes([0.81, 0.05, 0.1, 0.075])
        self.bnext = Button(axnext, 'Next')
        self.bnext.on_clicked(self.next)
        self.bprev = Button(axprev, 'Previous')
        self.bprev.on_clicked(self.prev)

    def next(self, event):
        self.ind += 1
        i = self.ind % len(self.freqs)
        ydata = np.sin(2*np.pi*self.freqs[i]*self.t)
        print('next')
        self.scope.set_ydata(ydata)
        plt.draw()

    def prev(self, event):
        self.ind -= 1
        i = self.ind % len(self.freqs)
        ydata = np.sin(2*np.pi*self.freqs[i]*self.t)
        print('next')
        self.scope.set_ydata(ydata)
        plt.draw()


#viewport = Gui()
#plt.show()
