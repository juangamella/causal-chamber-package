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

"""
Simulators for the wind tunnel phenomena.
"""


import numpy as np
from causalchamber.simulators import Simulator

# --------------------------------------------------------------------
# Simulator classes


class ModelA1(Simulator):
    """Simulator of the steady-state fan speed given the load.

    The derivation of the simulator, including inputs, outputs and
    parameters, is described under Model A1 in Appendix IV.1 of the
    paper "Causal chambers as a real-world physical testbed for AI
    Methodology" (2025) by Gamella et al.

    Link for direct access:
    https://arxiv.org/pdf/2404.11341#page=28&zoom=100,57,332

    """

    # Class variables: variable names of inputs, parameters and outputs
    inputs_names = ["load"]
    outputs_names = ["rpm"]

    def __init__(self, L_min, omega_max):
        """Initializes the simulator."""
        super(ModelA1, self).__init__()
        self.L_min = L_min
        self.omega_max = omega_max

    def parameters(self):
        """
        Return a dictionary with the simulator parameters and their values.
        """
        return {"L_min": self.L_min, "omega_max": self.omega_max}

    def _simulate(self, load, L_min, omega_max):
        """
        Simulate the steady-state fan speed using Model A1.

        This function computes the steady-state angular speed of the fan in radians per second
        using Model A1 and then converts the result to revolutions per minute (rpm).

        Parameters
        ----------
        load : float or array-like
            The fan load (or time series of loads) applied to the fan.
        L_min : float
            The minimum effective load. For load < L_min, L_min is used.
        omega_max : float
            The maximum angular speed of the fan (in rpm).

        Returns
        -------
        float or array-like
            The simulated fan speed in rpm.

        Notes
        -----
        Conversion from rad/s to rpm is performed using the factor (30 / π).
        This method is invoked by the class method `simulate_from_inputs`.
        """
        rads = model_a1(L=load, L_min=L_min, omega_max=omega_max * np.pi / 30)
        # Transform from rad/s to rpm
        return rads / np.pi * 30


class ModelA2(Simulator):
    """Simulator of the fan speed dynamics given the load through time.

    The derivation of the simulator, including inputs, outputs and
    parameters, is described under Model A2 in Appendix IV.1 of the
    paper "Causal chambers as a real-world physical testbed for AI
    Methodology" (2025) by Gamella et al.

    Link for direct access:
    https://arxiv.org/pdf/2404.11341#page=28&zoom=100,57,332

    """

    # Class variables: variable names of inputs, parameters and outputs
    inputs_names = ["load", "timestamp"]
    outputs_names = ["rpm"]

    def __init__(
        self,
        # Parameters
        I,
        tau,
        K,
        # Parameters for the ODE solver
        omega_0,
        simulation_steps=100,
    ):
        """Initializes the simulator."""
        super(ModelA2, self).__init__()
        # Parameters
        self.I = I
        self.tau = tau
        self.K = K
        self.omega_0 = omega_0
        self.simulation_steps = simulation_steps

    def parameters(self):
        """
        Return a dictionary with the simulator parameters and their values.
        """
        return {
            "I": self.I,
            "tau": self.tau,
            "K": self.K,
            "omega_0": self.omega_0,
            "simulation_steps": self.simulation_steps,
        }

    def _simulate(self, load, timestamp, I, tau, K, omega_0, simulation_steps):
        """
        Simulate the dynamic behavior of the fan using Model A2.

        This function integrates the fan’s speed over time using the torque-balance differential
        equation from Model A2. An ODE solver (Euler's method) is used with a specified number of
        simulation steps, and the output is converted from rad/s to rpm.

        See Model A2 in Appendix IV.1 for more details (https://arxiv.org/pdf/2404.11341#page=28&zoom=100,57,332).

        Parameters
        ----------
        load : array-like
            Time series of the fan load.
        timestamp : array-like
            The time points (in seconds) at which the simulation is computed.
        I : float
            The moment of inertia of the fan (kg·m²).
        tau : function
            A function that computes the motor torque as a function of load.
        K : float
            The drag constant representing the drag of the fan.
        omega_0 : float
            The initial angular speed of the fan (in rpm; note that the internal model works in rad/s).
        simulation_steps : int
            The number of steps used by the ODE solver (Euler's method).

        Returns
        -------
        float or array-like
            The simulated fan speed in rpm.

        Notes
        -----
        Conversion from rad/s to rpm is performed using the factor (30 / π).
        This method is invoked by the class method `simulate_from_inputs`.

        The torque function (tau) used in the original paper (see model A2 in Appendix IV) is given by:

        ```python
        def tau(load, C_min, C_max, L_min, T):
            load = np.atleast_1d(load)
            torques = T * (C_min + np.maximum(L_min, load) ** 3 * (C_max - C_min) - C_min)
            torques[load == 0] = 0
            return torques if len(load) > 1 else torques[0]
        ```
        """
        rads = model_a2(
            loads=load,
            timestamps=timestamp,
            I=I,
            tau=tau,
            K=K,
            omega_0=omega_0 * np.pi / 30,
            simulation_steps=simulation_steps,
        )
        # Transform from rad/s to rpm
        return rads / np.pi * 30


class ModelB1(Simulator):
    """Simulator of the fan current given its load.

    The derivation of the simulator, including inputs, outputs and
    parameters, is described under Model B1 in Appendix IV.1 of the
    paper "Causal chambers as a real-world physical testbed for AI
    Methodology" (2025) by Gamella et al.

    Link for direct access:
    https://arxiv.org/pdf/2404.11341#page=28&zoom=100,57,332

    """

    # Class variables: variable names of inputs, parameters and outputs
    inputs_names = ["load"]
    outputs_names = ["current"]

    def __init__(
        self,
        # Parameters
        C_min,
        C_max,
        L_min,
    ):
        """Initializes the simulator."""
        super(ModelB1, self).__init__()
        # Parameters
        self.C_min = C_min
        self.C_max = C_max
        self.L_min = L_min

    def parameters(self):
        """
        Return a dictionary with the simulator parameters and their values.
        """
        return {
            "C_min": self.C_min,
            "C_max": self.C_max,
            "L_min": self.L_min,
        }

    def _simulate(self, load, C_min, C_max, L_min):
        """Simulate the electrical current drawn by the fan using Model B1.

        This function computes the current drawn by the fan based on
        the applied load using the cubic relationship described in
        Model B1. When the load is zero, the no-load current is
        returned.

        Parameters
        ----------
        load : float or array-like
            The fan load.
        C_min : float
            The no-load current of the fan.
        C_max : float
            The maximum current drawn by the fan at full load.
        L_min : float
            The minimum effective load; for loads below this threshold, L_min is used.

        Returns
        -------
        float or array-like
            The simulated current (in Amperes) drawn by the fan.

        Notes
        -----
        This method is invoked by the class method `simulate_from_inputs`.
        """
        load = np.atleast_1d(load)
        current = C_min + np.maximum(load, L_min) ** 3 * (C_max - C_min)
        current[load == 0] = C_min
        return current if len(load) > 1 else current[0]


class SimA1C2(Simulator):
    """Simulator for the pressure measurements from the downwind barometer
    in the wind tunnel.

    The derivation of the simulator, including inputs, outputs and
    parameters, is described under Models A1 and C2 in the paper
    "Causal chambers as a real-world physical testbed for AI
    Methodology" (2025) by Gamella et al.

    Link for direct access:
    https://arxiv.org/pdf/2404.11341#page=28&zoom=100,57,332

    """

    # Class variables: variable names of inputs and outputs
    inputs_names = ["load_in", "load_out", "pressure_ambient"]
    outputs_names = ["pressure_downwind", "rpm_in", "rpm_out"]

    def __init__(
        self,
        # Parameters for model A1
        L_min,
        omega_max,
        # Parameters for model C2
        S_max,
        Q_max,
        r,
        # Sensor noise
        barometer_error,  # The barometer offset
        barometer_precision,  # The std. of the barometer sensor noise
        random_state=42,
    ):
        """Initializes the simulator."""
        super(SimA1C2, self).__init__()

        # Parameters for model A1
        self.L_min = L_min
        self.omega_max = omega_max

        # Parameters for model C2
        self.S_max = S_max
        self.Q_max = Q_max
        self.r = r

        # Sensor noise
        self.barometer_error = barometer_error
        self.barometer_precision = barometer_precision
        self.random_state = random_state

    def parameters(self):
        """
        Return a dictionary with the simulator parameters and their values.
        """
        return {
            "L_min": self.L_min,
            "omega_max": self.omega_max,
            "S_max": self.S_max,
            "Q_max": self.Q_max,
            "r": self.r,
            "barometer_error": self.barometer_error,
            "barometer_precision": self.barometer_precision,
            "random_state": self.random_state,
        }

    def _simulate(
        self,
        load_in,
        load_out,
        pressure_ambient,
        L_min,
        omega_max,
        # Parameters for model C2
        S_max,
        Q_max,
        r,
        # Sensor noise
        barometer_error,  # The barometer offset
        barometer_precision,  # The std. of the barometer sensor noise
        random_state,
    ):
        """
        Simulate wind tunnel conditions using Models A1 and C2.

        This function simulates the static pressure inside a wind tunnel by combining the
        steady-state fan speed model (Model A1) with the static pressure model (Model C2). It computes
        the downwind pressure and the speeds of both the intake and exhaust fans, converting the speeds
        from rad/s to rpm.

        Parameters
        ----------
        load_in : float or array-like
            The load applied to the intake fan.
        load_out : float or array-like
            The load applied to the exhaust fan.
        pressure_ambient : float
            The ambient static pressure (Pa) outside the wind tunnel.
        L_min : float
            The minimum effective load used in Model A1.
        omega_max : float
            The maximum fan speed (in rpm).
        S_max : float
            The maximum static pressure produced by the fan at full speed.
        Q_max : float
            The maximum airflow produced by the fan (in m³/s).
        r : float
            The airflow ratio parameter used in Model C2.
        barometer_error : float
            The offset error of the barometer sensor.
        barometer_precision : float
            The standard deviation of the barometer sensor noise.
        random_state : int or RandomState
            Seed or random state for simulating sensor noise.

        Returns
        -------
        tuple
            A tuple containing:
                - pressure_downwind (float or array-like): Simulated downwind static pressure (Pa).
                - rpm_in (float or array-like): Intake fan speed in rpm.
                - rpm_out (float or array-like): Exhaust fan speed in rpm.

        Notes
        -----
        Fan speeds are converted from rad/s to rpm using the factor (30 / π).
        This method is invoked by the class method `simulate_from_inputs`.
        """
        pressure_downwind, omega_in, omega_out = simulator_a1_c2(
            load_in=load_in,
            load_out=load_out,
            hatch=None,  # ignore hatch input
            P_amb=pressure_ambient,
            L_min=L_min,
            omega_max=omega_max * np.pi / 30,  # convert to rad/s
            # Parameters for model C2
            S_max=S_max,
            Q_max=Q_max,
            r=r,
            # Sensor noise
            barometer_error=barometer_error,  # The barometer offset
            barometer_precision=barometer_precision,  # The std. of the barometer sensor noise
            random_state=random_state,
        )
        rpm_in = omega_in / np.pi * 30
        rpm_out = omega_out / np.pi * 30
        return pressure_downwind, rpm_in, rpm_out


class SimA1C3(Simulator):
    """Simulator for the pressure measurements from the downwind barometer
    in the wind tunnel.

    The derivation of the simulator, including inputs, outputs and
    parameters, is described under Models A1 and C3 in the paper
    "Causal chambers as a real-world physical testbed for AI
    Methodology" (2025) by Gamella et al.

    Link for direct access:
    https://arxiv.org/pdf/2404.11341#page=28&zoom=100,57,332

    See more details in the `_simulate` method.

    """

    # Class variables: variable names of inputs, parameters, and outputs
    inputs_names = ["load_in", "load_out", "hatch", "pressure_ambient"]
    outputs_names = ["pressure_downwind", "rpm_in", "rpm_out"]

    def __init__(
        self,
        # Parameters for model A1
        L_min,
        omega_max,
        # Parameters for model C3
        S_max,
        Q_max,
        r_0,
        beta,
        # Sensor noise
        barometer_error,  # The barometer offset
        barometer_precision,  # The std. of the barometer sensor noise
        random_state=42,
    ):
        """Initializes the simulator with the given parameters. . See the
        docstring for `_simulate` for a full description of the simulator
        parameters."""
        super(SimA1C3, self).__init__()

        # Parameters for models A1 and C3
        self.L_min = L_min
        self.omega_max = omega_max
        self.S_max = S_max
        self.Q_max = Q_max
        self.r_0 = r_0
        self.beta = beta

        # Sensor noise parameters
        self.barometer_error = barometer_error
        self.barometer_precision = barometer_precision
        self.random_state = random_state

    def parameters(self):
        """Return a dictionary with the simulator parameters and their values."""
        return {
            "L_min": self.L_min,
            "omega_max": self.omega_max,
            "S_max": self.S_max,
            "Q_max": self.Q_max,
            "r_0": self.r_0,
            "beta": self.beta,
            "barometer_error": self.barometer_error,
            "barometer_precision": self.barometer_precision,
            "random_state": self.random_state,
        }

    def _simulate(
        self,
        load_in,
        load_out,
        hatch,
        pressure_ambient,
        L_min,
        omega_max,
        S_max,
        Q_max,
        r_0,
        beta,
        barometer_error,
        barometer_precision,
        random_state,
    ):
        """
        Simulate wind tunnel conditions using Models A1 and C3.

        This function computes the downwind static pressure as well as the intake and exhaust fan speeds
        by combining the steady-state fan model (Model A1) with the static pressure model that accounts for
        the hatch position (Model C3). The fan speeds are converted from rad/s to rpm.

        Parameters
        ----------
        load_in : float or array-like
            The load applied to the intake fan.
        load_out : float or array-like
            The load applied to the exhaust fan.
        hatch : float or array-like
            The hatch position, in degrees.
        pressure_ambient : float
            The ambient static pressure (Pa) outside the wind tunnel.
        L_min : float
            The minimum effective load parameter for the fan model.
        omega_max : float
            The maximum fan speed (in rpm).
        S_max : float
            The maximum static pressure produced by the fan at full speed.
        Q_max : float
            The maximum airflow produced by the fan (in m³/s).
        r_0 : float
            The baseline airflow ratio when the hatch is closed.
        beta : float
            The coefficient representing the linear effect of the hatch position on the airflow ratio.
        barometer_error : float
            The offset error of the barometer sensor.
        barometer_precision : float
            The standard deviation of the barometer sensor noise.
        random_state : int or RandomState
            Seed or random state for simulating sensor noise.

        Returns
        -------
        tuple
            A tuple containing:
                - pressure_downwind (float or array-like): Simulated downwind static pressure (Pa).
                - rpm_in (float or array-like): Intake fan speed in rpm.
                - rpm_out (float or array-like): Exhaust fan speed in rpm.

        Notes
        -----
        Fan speeds are converted from rad/s to rpm using the factor (30 / π).
        This method is invoked by the class method `simulate_from_inputs`.

        """
        pressure_downwind, omega_in, omega_out = simulator_a1_c3(
            load_in=load_in,
            load_out=load_out,
            hatch=hatch,
            P_amb=pressure_ambient,
            L_min=L_min,
            omega_max=omega_max * np.pi / 30,  # convert to rad/s
            S_max=S_max,
            Q_max=Q_max,
            r_0=r_0,
            beta=beta,
            barometer_error=barometer_error,
            barometer_precision=barometer_precision,
            random_state=random_state,
        )
        rpm_in = omega_in / np.pi * 30
        rpm_out = omega_out / np.pi * 30
        return pressure_downwind, rpm_in, rpm_out


class SimA2C3(Simulator):
    """Simulator for the pressure measurements from the downwind barometer
    in the wind tunnel.

    The derivation of the simulator, including inputs, outputs and
    parameters, is described under Models A2 and C3 in the paper
    "Causal chambers as a real-world physical testbed for AI
    Methodology" (2025) by Gamella et al.

    Link for direct access:
    https://arxiv.org/pdf/2404.11341#page=28&zoom=100,57,332

    """

    # Class variables: variable names of inputs, parameters, and outputs
    inputs_names = ["load_in", "load_out", "hatch", "pressure_ambient", "timestamp"]
    outputs_names = ["pressure_downwind", "omega_in", "omega_out"]

    def __init__(
        self,
        # Parameters for model A2
        I,
        tau,
        K,
        omega_in_0,
        omega_out_0,
        # Parameters for model C3
        S_max,
        omega_max,
        Q_max,
        r_0,
        beta,
        # Sensor noise
        barometer_error,  # The barometer offset
        barometer_precision,  # The std. of the barometer sensor noise
        random_state=42,
        # For the ODE solver of model A2
        simulation_steps=100,
    ):
        """Initializes the simulator with the given parameters. See the
        docstring for `_simulate` for a full description of the simulator
        parameters."""
        super(SimA2C3, self).__init__()

        # Parameters for models A2 and C3
        self.I = I
        self.tau = tau
        self.K = K
        self.omega_in_0 = omega_in_0
        self.omega_out_0 = omega_out_0
        self.S_max = S_max
        self.omega_max = omega_max
        self.Q_max = Q_max
        self.r_0 = r_0
        self.beta = beta

        # Sensor noise parameters
        self.barometer_error = barometer_error
        self.barometer_precision = barometer_precision
        self.random_state = random_state

        # ODE solver parameter
        self.simulation_steps = simulation_steps

    def parameters(self):
        """Return a dictionary with the simulator parameters and their values."""
        return {
            "I": self.I,
            "tau": self.tau,
            "K": self.K,
            "omega_in_0": self.omega_in_0,
            "omega_out_0": self.omega_out_0,
            "S_max": self.S_max,
            "omega_max": self.omega_max,
            "Q_max": self.Q_max,
            "r_0": self.r_0,
            "beta": self.beta,
            "barometer_error": self.barometer_error,
            "barometer_precision": self.barometer_precision,
            "random_state": self.random_state,
            "simulation_steps": self.simulation_steps,
        }

    def _simulate(
        self,
        # Inputs
        load_in,
        load_out,
        hatch,
        pressure_ambient,
        timestamp,
        # Parameters for model A2
        I,
        tau,
        K,
        omega_in_0,
        omega_out_0,
        # Parameters for model C3
        S_max,
        omega_max,
        Q_max,
        r_0,
        beta,
        # Parameters for noise simulation
        barometer_error,
        barometer_precision,
        random_state,
        simulation_steps,
    ):
        """
        Simulate dynamic wind tunnel behavior using Models A2 and C3.

        This function combines the dynamic fan speed simulation from Model A2 with the static
        pressure model that accounts for hatch position (Model C3). It computes the evolution
        of the downwind static pressure along with the intake and exhaust fan speeds over time.
        The fan speeds are internally calculated in radians per second and then converted to
        revolutions per minute (rpm) using the conversion factor (30 / π).

        The inputs (load_in, load_out, hatch, pressure_ambient and timestamp) are time-series.

        Parameters
        ----------
        load_in : float or array-like
            The load applied to the intake fan.
        load_out : float or array-like
            The load applied to the exhaust fan.
        hatch : float or array-like
            The hatch position affecting the system impedance.
        pressure_ambient : float
            The ambient static pressure (Pa) outside the wind tunnel.
        timestamp : array-like
            Time stamps (in seconds) at which the simulation is evaluated.
        I : float
            The moment of inertia of the fan (kg·m²), used in Model A2.
        tau : function
            A function that computes the motor torque as a function of load for Model A2.
        K : float
            The drag constant in the torque-balance equation of Model A2.
        omega_in_0 : float
            The initial intake fan speed (in rpm; note that internal computations use rad/s).
        omega_out_0 : float
            The initial exhaust fan speed (in rpm; note that internal computations use rad/s).
        S_max : float
            The maximum static pressure produced by the fan at full speed (Pa) in Model C3.
        omega_max : float
            The maximum fan speed (in rpm) in Model C3.
        Q_max : float
            The maximum airflow produced by the fan (m³/s) in Model C3.
        r_0 : float
            The baseline airflow ratio when the hatch is closed in Model C3.
        beta : float
            The coefficient representing the linear effect of the hatch position on the airflow ratio.
        barometer_error : float
            The offset error of the barometer sensor.
        barometer_precision : float
            The standard deviation of the barometer sensor noise.
        random_state : int or RandomState
            Seed or random state for simulating sensor noise.
        simulation_steps : int
            The number of simulation steps used by the internal ODE solver (Euler's method).

        Returns
        -------
        tuple
            A tuple containing:
                - pressure_downwind (float or array-like): The simulated downwind static pressure (Pa).
                - rpm_in (float or array-like): The simulated intake fan speed in rpm.
                - rpm_out (float or array-like): The simulated exhaust fan speed in rpm.

        Notes
        -----
        Fan speeds are converted from rad/s to rpm using the factor (30 / π).
        This method is invoked by the class method `simulate_from_inputs`.
        """
        pressure_downwind, omega_in, omega_out = simulator_a2_c3(
            load_in=load_in,
            load_out=load_out,
            hatch=hatch,
            P_amb=pressure_ambient,
            timestamps=timestamp,
            I=I,
            tau=tau,
            C=K,
            omega_in_0=omega_in_0 * np.pi / 30,  # convert to rad/s
            omega_out_0=omega_out_0 * np.pi / 30,
            S_max=S_max,
            omega_max=omega_max * np.pi / 30,
            Q_max=Q_max,
            r_0=r_0,
            beta=beta,
            barometer_error=barometer_error,
            barometer_precision=barometer_precision,
            random_state=random_state,
            simulation_steps=simulation_steps,
        )
        rpm_in = omega_in / np.pi * 30
        rpm_out = omega_out / np.pi * 30
        return pressure_downwind, rpm_in, rpm_out


# --------------------------------------------------------------------
# Mechanistic models of the wind tunnel processes

# These are called from the _simulate function of each simulator
# class. This redundancy is done to clearly separate the unit conversion
# between RPMs and rad/s for models A1 and A2.

# For the derivation and more details about each model and its
# parameters, see Appendix IV.1 of the paper "Causal chambers as a
# real-world physical testbed for AI Methodology" (2025) by Gamella et
# al.

# Link for direct access:
# https://arxiv.org/pdf/2404.11341#page=28&zoom=100,57,332


def model_a1(
    # Input
    L,
    # Parameters
    L_min,
    omega_max,
):
    """Model A1 of the steady-state fan speed given the load."""
    L = np.atleast_1d(L)
    omega = np.maximum(L, L_min) * omega_max
    omega[L == 0] = 0
    return omega if len(L) > 1 else omega[0]


def model_a2(
    # Input
    loads,
    # Parameters
    I,
    tau,
    K,
    # Parameters for the ODE solver
    omega_0,
    timestamps,
    simulation_steps,
):
    """Model A2 of the fan-speed dynamics given a time-series of the fan
    load."""
    # Compute torque at each time point
    torques = tau(loads)

    # Compute speed at each time point by solving the ODE
    omegas = np.zeros_like(loads, dtype=float)
    omegas[0] = omega_0
    for i in range(1, len(loads)):
        timestep = timestamps[i] - timestamps[i - 1]
        torque = torques[i]
        omega = omegas[i - 1]
        dt = timestep / simulation_steps
        for _ in range(simulation_steps):
            d_omega = 1 / I * (torque - K * omega**2)
            omega += dt * d_omega
        omegas[i] = omega
    return omegas


def model_c1(
    # Input
    omega_in,
    omega_out,
    P_amb,
    # Parameters
    S_max,
    omega_max,
):
    """Model C1 of the effect of the loads and hatch on the downwind barometer"""
    return (
        P_amb
        + S_max * (omega_in / omega_max) ** 2
        - S_max * (omega_out / omega_max) ** 2
    )


def model_c2(
    # Input
    omega_in,
    omega_out,
    P_amb,
    # Parameters
    S_max,
    omega_max,
    Q_max,
    r,
):
    """Model C2 of the effect of the loads and hatch on the downwind barometer"""
    S_r = lambda omega: _S_r(omega, r, Q_max, S_max, omega_max)
    return P_amb + S_r(omega_in) - S_r(omega_out)


def model_c3(
    # Input
    omega_in,
    omega_out,
    H,
    P_amb,
    # Parameters
    S_max,
    omega_max,
    Q_max,
    r_0,
    beta,
):
    """Model C3 of the effect of the loads and hatch on the downwind barometer"""
    # Compute impedance (airflow ratio) as a function of the hatch position H
    r = np.minimum(1, r_0 + beta * H / 45)
    S_rh = lambda omega: _S_r(omega, r, Q_max, S_max, omega_max)
    return P_amb + S_rh(omega_in) - S_rh(omega_out)


def _S_r(
    omega,
    r,
    Q_max,
    S_max,
    omega_max,
):
    """Used in models C2 and C3 to compute the static pressure produced by
    the fan, as the intersection of the impedance curve (for airflow
    ratio r) and the (linear) PQ-characteristic. See the manuscript for more details.

    """
    Z = S_max / Q_max**2 * (1 - r) / r**2
    # Find the intersection of the impedance curve S = ZQ^2 and the PQ-characteristic
    #   solve aQ^2 + bQ + c = 0 using the quadratic formula, where
    a = Z
    b = (omega / omega_max) * S_max / Q_max
    c = -((omega / omega_max) ** 2) * S_max
    # Intersection (Q,S)
    Q = (-b + np.sqrt(b**2 - 4 * a * c)) / 2 / a  # produced airflow
    S = Z * Q**2  # produced static pressure
    return S


def simulator_a1_c2(
    # Input
    load_in,
    load_out,
    hatch,
    P_amb,
    # Parameters for model A1
    L_min,
    omega_max,
    # Parameters for model C2
    S_max,
    Q_max,
    r,
    # Sensor noise
    barometer_error,  # The barometer offset
    barometer_precision,  # The std. of the barometer sensor noise
    random_state=42,
):
    load_in, load_out = np.array(load_in), np.array(load_out)
    omega_in = model_a1(load_in, L_min, omega_max)
    omega_out = model_a1(load_out, L_min, omega_max)
    P_dw = model_c2(omega_in, omega_out, P_amb, S_max, omega_max, Q_max, r)
    rng = np.random.default_rng(random_state)
    P_dw += rng.normal(barometer_error, barometer_precision, size=len(P_dw))
    return P_dw, omega_in, omega_out


def simulator_a1_c3(
    # Input
    load_in,
    load_out,
    hatch,
    P_amb,
    # Parameters for model A1
    L_min,
    omega_max,
    # Parameters for model C3
    S_max,
    Q_max,
    r_0,
    beta,
    # Sensor noise
    barometer_error,  # The barometer offset
    barometer_precision,  # The std. of the barometer sensor noise
    random_state=42,
):
    load_in, load_out = np.array(load_in), np.array(load_out)
    omega_in = model_a1(load_in, L_min, omega_max)
    omega_out = model_a1(load_out, L_min, omega_max)
    P_dw = model_c3(
        omega_in, omega_out, hatch, P_amb, S_max, omega_max, Q_max, r_0, beta
    )
    rng = np.random.default_rng(random_state)
    P_dw += rng.normal(barometer_error, barometer_precision, size=len(P_dw))
    return P_dw, omega_in, omega_out


def simulator_a2_c3(
    # Input
    load_in,
    load_out,
    hatch,
    P_amb,
    # Parameters for model A1
    I,
    tau,
    C,
    timestamps,
    omega_in_0,
    omega_out_0,
    # Parameters for model C3
    S_max,
    omega_max,
    Q_max,
    r_0,
    beta,
    # Sensor noise
    barometer_error,  # The barometer offset
    barometer_precision,  # The std. of the barometer sensor noise
    random_state=42,
    # For the ODE solver of model a2
    simulation_steps=100,
):
    load_in, load_out = np.array(load_in), np.array(load_out)
    omega_in = model_a2(load_in, I, tau, C, omega_in_0, timestamps, simulation_steps)
    omega_out = model_a2(load_out, I, tau, C, omega_out_0, timestamps, simulation_steps)
    P_dw = model_c3(
        omega_in, omega_out, hatch, P_amb, S_max, omega_max, Q_max, r_0, beta
    )
    rng = np.random.default_rng(random_state)
    P_dw += rng.normal(barometer_error, barometer_precision, size=len(P_dw))
    return P_dw, omega_in, omega_out
