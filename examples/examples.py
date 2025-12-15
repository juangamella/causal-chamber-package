# Examples used in the README.md

# ----------------------------------------------------------------------
# Datasets

import causalchamber.datasets as datasets

# Download the dataset and store it, e.g., in the current directory
dataset = datasets.Dataset(name="lt_camera_test_v1", root="./", download=True)

# Select an experiment and load the observations and images
experiment = dataset.get_experiment(name="palette")
observations = experiment.as_pandas_dataframe()
images = experiment.as_image_array(size="200")

print(dataset.available_experiments())
print(experiment.available_sizes())

import causalchamber

print(causalchamber.datasets.list_available())

# ----------------------------------------------------------------------
# Ground truth


from causalchamber.ground_truth import graph

print(graph(chamber="lt", configuration="standard"))

# Output:

#              red  green  blue  osr_c  v_c  current  pol_1  pol_2  osr_angle_1  \
# red            0      0     0      0    0        1      0      0            0
# green          0      0     0      0    0        1      0      0            0
# blue           0      0     0      0    0        1      0      0            0
# osr_c          0      0     0      0    0        1      0      0            0

from causalchamber.ground_truth import latex_name

print(latex_name("pol_1", enclose=True))

# Output:

# '$\\theta_1$'

# ----------------------------------------------------------------------
# Models

import numpy as np
from causalchamber.models import model_a1

print(model_a1(L=np.linspace(0, 1, 10), L_min=0.1, omega_max=314.15))

# Output:

# array([ 31.415     ,  34.90555556,  69.81111111, 104.71666667,
#        139.62222222, 174.52777778, 209.43333333, 244.33888889,
#        279.24444444, 314.15      ])
