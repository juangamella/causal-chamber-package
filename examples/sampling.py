# MIT License

# Copyright (c) 2025 Juan L. Gamella, Causal Chamber GmbH

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


import numpy as np
import matplotlib.pyplot as plt

def bounded_random_walk(n, lo, hi, start=None, step_size=1.0, random_state=None):
    """Generate a random walk bounded between lo and hi with reflection at boundaries.
    
    Parameters:
    -----------
    n : int
        Number of steps in the random walk
    lo : float
        Lower boundary
    hi : float
        Upper boundary
    start : float, optional
        Starting position of the walk. If None (default), a value is
        sampled uniformly at random between lo and hi.
    step_size : float, optional
        Standard deviation of the random step (default: 1.0)
    random_state : integer, optional
        The seed for the random number generator.
    
    Returns:
    --------
    numpy.ndarray
        Array of positions for the random walk

    """
    if lo >= hi:
        raise ValueError("lo must be less than hi")

    # Start random-number generator
    rng = np.random.default_rng(random_state)
    
    # Initialize starting position
    if start is None:
        start = rng.uniform(lo, hi)
    elif start < lo or start > hi:
        raise ValueError(f"start must be between lo ({lo}) and hi ({hi})")
    
    # Initialize walk
    walk = np.zeros(n)
    walk[0] = start
    
    # Generate random walk with reflection
    for i in range(1, n):
        # Take a random step
        step = rng.normal(0, step_size)
        new_position = walk[i-1] + step
        
        # Reflect if outside boundaries
        while new_position < lo or new_position > hi:
            if new_position < lo:
                # Reflect off lower boundary
                new_position = lo + (lo - new_position)
            elif new_position > hi:
                # Reflect off upper boundary
                new_position = hi - (new_position - hi)
        
        walk[i] = new_position
    
    return walk
