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

import time

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

# Once status is 'DONE' you can download the data:

print(f"Waiting for experiment {experiment_id} to finish")
while rlab.get_experiment(experiment_id)['status'] != 'DONE':
    time.sleep(2)
    print(".", end="")
print()

dataset = rlab.download_data(experiment_id, root='/tmp')
observations = dataset.dataframe

# from examples.plotting import plot_wt
# plot_wt(observations)

