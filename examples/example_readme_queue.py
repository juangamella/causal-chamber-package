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

"""
README example code for queue mode:
"""


import causalchamber.lab as lab

# Connect to the Remote Lab
rlab = lab.Lab(credentials_file = '.credentials')

# Start a new experiment protocol
experiment = rlab.new_experiment(chamber_id = 'wt-demo-ch4lu', config ='full')

# Write the experiment protocol
experiment.wait(7_000) # Wait 7s for fan speed to stabilize after reset
experiment.measure(n=80) # Measure base state
experiment.set('load_in', 1.0) # Turn intake fan to max
experiment.measure(n=20) # Measure impulse state
experiment.set('load_in', 0.01) # Idle intake fan
experiment.measure(n=80) # Measure base state
    
# Submit the experiment
experiment_id = experiment.submit(tag='demo-queue')

# You can monitor the status of the experiment
rlab.get_experiments(print_max=1)

#   Status    Tag   Experiment ID                          Chamber ID      Config   Submitted On                    
# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
#   RUNNING         27d733f7-bec1-4202-8179-253dd63fef66   wt-demo-ch4lu   full     Mon, Dec 15, 2025 16:39:48 CET  

#   --- showing 1 / 1803 experiments ---
# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
#  Date/time in your machine's local timezone — current time = Mon, Dec 15, 2025 16:40:06 CET

# Once status is 'DONE' you can download the data:

dataset = rlab.download_data(experiment_id, root='/tmp')
observations = dataset.dataframe

from examples.plotting import plot_wt
plot_wt(observations)

