# MIT License

# Copyright (c) 2025 Causal Chamber GmbH

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Authors:
#   - Juan L. Gamella [juan@causalchamber.ai]

"""Numpy implementation of the deterministic simulator of the
light-tunnel sensors.
"""

import numpy as np
from copy import deepcopy
from causalchamber.simulators import Simulator


class Deterministic(Simulator):
    # Class variables: variable names of inputs, parameters and outputs
    inputs_names = [
        "red",
        "green",
        "blue",
        "pol_1",
        "pol_2",
        "diode_ir_1",
        "diode_ir_2",
        "diode_ir_3",
        "diode_vis_1",
        "diode_vis_2",
        "diode_vis_3",
        "t_ir_1",
        "t_ir_2",
        "t_ir_3",
        "t_vis_1",
        "t_vis_2",
        "t_vis_3",
        "v_c",
        "v_angle_1",
        "v_angle_2",
    ]
    outputs_names = [
        "ir_1",
        "vis_1",
        "ir_2",
        "vis_2",
        "ir_3",
        "vis_3",
        "current",
        "angle_1",
        "angle_2",
    ]
    parameters_names = [
        "S",
        "d1",
        "d2",
        "d3",
        "Ts",
        "Tp",
        "Tc",
        "Q",
        "C0",
        "A",
        "a1",
        "a2",
    ]

    def __init__(self, S, d1, d2, d3, Ts, Tp, Tc, Q, C0, A, a1, a2):
        super(Deterministic, self).__init__()
        self.S = deepcopy(S)
        self.d1 = d1
        self.d2 = d2
        self.d3 = d3
        self.Ts = deepcopy(Ts)
        self.Tp = deepcopy(Tp)
        self.Tc = deepcopy(Tc)
        self.Q = deepcopy(Q)
        self.C0 = deepcopy(C0)
        self.A = deepcopy(A)
        self.a1 = deepcopy(a1)
        self.a2 = deepcopy(a2)

    def parameters(self):
        return {
            "S": self.S,
            "d1": self.d1,
            "d2": self.d2,
            "d3": self.d3,
            "Ts": self.Ts,
            "Tp": self.Tp,
            "Tc": self.Tc,
            "Q": self.Q,
            "C0": self.C0,
            "A": self.A,
            "a1": self.a1,
            "a2": self.a2,
        }

    def _simulate(
        self,
        # Simulator inputs
        red,
        green,
        blue,
        pol_1,
        pol_2,
        diode_ir_1,
        diode_ir_2,
        diode_ir_3,
        diode_vis_1,
        diode_vis_2,
        diode_vis_3,
        t_ir_1,
        t_ir_2,
        t_ir_3,
        t_vis_1,
        t_vis_2,
        t_vis_3,
        v_c,
        v_angle_1,
        v_angle_2,
        # Simulator parameters
        S,
        d1,
        d2,
        d3,
        Ts,
        Tp,
        Tc,
        Q,
        C0,
        A,
        a1,
        a2,
    ):
        """Simulates the light-intensity measurements from the sensors in the
        light tunnel. For the complete derivation and details of all
        parameters, see Appendix C of the paper "Sanity Checking
        Causal Representation Learning on a Simple Real-World System"
        (2025) by Juan L. Gamella*, Simon Bing*, and Jakob Runge.

        Link for direct access: TODO

        The function takes as input the values of the tunnel actuators
        (light-source color, polarizer positions and light-sensor
        parameters), various simulation parameters, and returns the
        uncalibrated infrared and visible-light intensity
        measurements, as well as the current and angle measurements.

        Parameters
        ----------
        red, green, blue : array_like
            1D arrays representing the brightness settings of the red,
            green, and blue LEDs respectively, each in the range [0,
            255].
        pol_1, pol_2 : array_like
            1D arrays representing the positions of the tunnel's
            polarizers in degrees, in the range [-180, 180].
        diode_ir_1, diode_ir_2, diode_ir_3 : array_like
            1D arrays representing the sizes of the infrared
            photodiodes used by the light sensors. Values are 0
            (small), 1 (medium), or 2 (large).
        diode_vis_1, diode_vis_2, diode_vis_3 : array_like
            1D arrays representing the sizes of the visible-light
            photodiodes used by the light sensors. Values are 0
            (small), 1 (medium), or 2 (large).
        t_ir_1, t_ir_2, t_ir_3 : array_like
            1D arrays representing the exposure time for the infrared
            sensors during measurements. Values are integers in the
            range [0, 3].
        t_vis_1, t_vis_2, t_vis_3 : array_like
            1D arrays representing the exposure time for the
            visible-light sensors during measurements. Values are
            integers in the range [0, 3].
        S : array_like, shape (2, 3)
            The linear response matrix of the photodiodes to the red,
            green, and blue light.  The first row corresponds to the
            response of the smallest IR photodiode, and the second row
            corresponds to the smallest visible-light photodiode.
        d1, d2, d3 : float
            The distances (in millimeters) from the tunnel's light
            source to the first, second, and third sensors
            respectively.
        Ts : np.ndarray
            The transmission rate (scaling of light intensity) for
            each color wavelength of the first polarizer (vector of
            length 3).
        Tp : np.ndarray
            Transmission rates for each color when the polarizers are
            aligned (vector of length 3).
        Tc : np.ndarray
            Transmission rates for each color when the polarizers are
            perpendicular(vector of length 3).
        Q : np.ndarray
            1 x 3 matrix that encodes the linear response of the
            current sensor to the brightness setting of each color.
        C0 : float
            The current drawn by the light source when it is turned
            off, i.e., `red=green=blue=0`. The value corresponds to
            the uncalibrated measurement when `v_c=5`.
        A : float
            The linear coefficient relating the change in polarizer
            position to the change in the voltage reading of the angle
            sensor, when the reference voltages are `v_angle_1=5` and
            `v_angle_2=5`, respectively.
        a1, a2: float
            The zero point of the angle sensors, i.e., the voltage
            reading when the polarizer positions are `pol_1=0` and
            `pol_2=0`, respectively, and the reference voltages are
            `v_angle_1=v_angle_2=5`.

        Returns
        -------
        ir_1 : numpy.ndarray
            Uncalibrated infrared light-intensity measurements from the first sensor.
        vis_1 : numpy.ndarray
            Uncalibrated visible light-intensity measurements from the first sensor.
        ir_2 : numpy.ndarray
            Uncalibrated infrared light-intensity measurements from the second sensor.
        vis_2 : numpy.ndarray
            Uncalibrated visible light-intensity measurements from the second sensor.
        ir_3 : numpy.ndarray
            Uncalibrated infrared light-intensity measurements from the third sensor.
        vis_3 : numpy.ndarray
            Uncalibrated visible light-intensity measurements from the third sensor.
        current : numpy.ndarray
            Simulated measurements of the current drawn by the light source, in Amperes.
        angle_1 : numpy.ndarray
            Simulated measurements of the angle sensor for the first polarizer.
        angle_2 : numpy.ndarray
            Simulated measurements of the angle sensor for the second polarizer.

        """

        RGB = np.array([red, green, blue])

        # First sensor
        SRGB = S @ RGB
        ir_1 = 2 ** (diode_ir_1 + t_ir_1) * SRGB[0]
        vis_1 = 2 ** (diode_vis_1 + t_vis_1) * SRGB[1]

        # Second sensor
        SRGB = S @ np.diag(Ts) @ ((d1 / d2) ** 2 * RGB)
        ir_2 = 2 ** (diode_ir_2 + t_ir_2) * SRGB[0]
        vis_2 = 2 ** (diode_vis_2 + t_vis_2) * SRGB[1]

        # Third sensor
        malus = np.atleast_2d(np.cos(np.deg2rad(pol_1 - pol_2)) ** 2)
        CRGB = (d1 / d3) ** 2 * RGB
        CRGB = np.diag(Tp - Tc) @ (malus * CRGB) + np.diag(Tc) @ CRGB
        SRGB = S @ CRGB
        ir_3 = 2 ** (diode_ir_3 + t_ir_3) * SRGB[0]
        vis_3 = 2 ** (diode_vis_3 + t_vis_3) * SRGB[1]

        # Current
        current = (Q @ RGB + C0) * 5.0 / v_c

        # Angles
        angle_1 = np.minimum((A * pol_1 + a1) * 5.0 / v_angle_1, 1023)
        angle_2 = np.minimum((A * pol_2 + a2) * 5.0 / v_angle_2, 1023)

        return ir_1, vis_1, ir_2, vis_2, ir_3, vis_3, current, angle_1, angle_2
