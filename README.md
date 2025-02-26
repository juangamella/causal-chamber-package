# Welcome to the `causalchamber` package!

[![PyPI version](https://badge.fury.io/py/causalchamber.svg)](https://badge.fury.io/py/causalchamber)
[![Downloads](https://static.pepy.tech/badge/causalchamber)](https://pepy.tech/project/causalchamber)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Donate](https://img.shields.io/static/v1.svg?logo=Github%20Sponsors&label=donate&message=Github%20Sponsors&color=e874ff)](https://github.com/sponsors/juangamella)

![The Causal Chambers: (left) the wind tunnel, and (right) the light tunnel with the front panel removed to show its interior.](https://causalchamber.s3.eu-central-1.amazonaws.com/downloadables/the_chambers.jpg)

The `causalchamber` package provides different functionality for the [Causal Chambers](https://causalchamber.ai):

- **[Remote API](#remote-api)**: a Python interface to remotely access our pool of chambers and run your own experiments.
- **[Datasets](#datasets)**: download existing datasets from the [dataset repository](https://github.com/juangamella/causal-chamber) directly into your Python code.
- **[Simulators](#simulators)**: run simulators and mechanistic models of different chamber phenomena.
- **[Ground truth](#ground-truth)**: load the ground-truth causal graphs and other information for each chamber.

If you use this package for your scientific work, please consider citing:

```
﻿@article{gamella2025chamber,
  author={Gamella, Juan L. and Peters, Jonas and B{\"u}hlmann, Peter},
  title={Causal chambers as a real-world physical testbed for {AI} methodology},
  journal={Nature Machine Intelligence},
  doi={10.1038/s42256-024-00964-x},
  year={2025},
}
```

## Install

You can install the package via pip, i.e. by typing

```
pip install causalchamber
```

in an appropriate shell.

## Remote API

We are currently building the API to remotely control the chambers and run your own experiments.

> You can request access to the API [here](https://tally.so/r/wbNe0e).

## Datasets

You can download existing datasets from the [dataset repository](https://github.com/juangamella/causal-chamber) directly into your Python code. For example, you can load the [`lt_camera_test_v1`](https://github.com/juangamella/causal-chamber/tree/main/datasets/lt_camera_test_v1) image dataset as follows:

```python
import causalchamber.datasets as datasets

# Download the dataset and store it, e.g., in the current directory
dataset = datasets.Dataset(name='lt_camera_test_v1', root='./', download=True)

# Select an experiment and load the observations and images
experiment = dataset.get_experiment(name='palette')
observations = experiment.as_pandas_dataframe()
images = experiment.as_image_array(size='200')
```

If `download=True`, the dataset will be downloaded and stored in the path provided by the `root` argument. If the dataset has already been downloaded it will not be downloaded again[^1]. The available experiments are documented in the dataset's [page](https://github.com/juangamella/causal-chamber/tree/main/datasets/lt_camera_test_v1), and can be listed by calling `dataset.available_experiments()` in the above example.

The image sizes available for a particular experiment can be listed by calling `experiment.available_sizes()` in the above example.

For a list of all the available datasets you can visit the [dataset repository](https://github.com/juangamella/causal-chamber) or call
```python
causalchamber.datasets.list_available()
```
The package refreshes its list of available datasets every time it's freshly imported.

[^1]: This also means you must delete the dataset yourself if you want to download a fresh copy. This is on purpose :)

## Simulators

The package also contains Python implementations of different simulators of chamber phenomena, including the mechanistic models described in [Appendix IV](https://arxiv.org/pdf/2404.11341#page=28&zoom=100,57,65) of the original [paper](https://www.nature.com/articles/s42256-024-00964-x).

> See the [Simulator Index](causalchamber/simulators/) for the complete documentation and examples.

## Ground truth

For evaluation and visualization, you can directly load the ground-truth causal graphs for the different chambers and their configurations. For example, to load the causal graphs given in [Fig. 3](https://www.nature.com/articles/s42256-024-00964-x/figures/3) of the original [paper](https://www.nature.com/articles/s42256-024-00964-x):

```python
from causalchamber.ground_truth import graph
graph(chamber="lt", configuration="standard")

# Output:

#              red  green  blue  osr_c  v_c  current  pol_1  pol_2  osr_angle_1  \
# red            0      0     0      0    0        1      0      0            0   
# green          0      0     0      0    0        1      0      0            0   
# blue           0      0     0      0    0        1      0      0            0   
# osr_c          0      0     0      0    0        1      0      0            0   
```

The graph adjacencies are also available as matrices [here](causalchamber/ground_truth/adjacencies/), where an edge `i->j` is denoted by a non-zero entry in the i<sup>th</sup> row + j<sup>th</sup> column.

To make it easier to plot graphs and reference them back to the original paper, the latex representation of each variable can be obtained by calling the `latex_name` function. For example, to obtain the latex representation $\theta_1$ of the `pol_1` variable, you can run

```python
from causalchamber.ground_truth import latex_name
latex_name('pol_1', enclose=True)

# Output:

# '$\\theta_1$'
```

Setting `enclose=False` will return the name without surrounding `$`. The complete mapping between variable names and latex symbols is given in [Appendix II](https://arxiv.org/pdf/2404.11341#page=17&zoom=100,57,65) of the original [paper](https://www.nature.com/articles/s42256-024-00964-x).

## Versioning

Non backward-compatible changes to the package are reflected by a change to the minor or major version number,

> e.g. *code that uses causalchamber==0.1.2 will run with causalchamber==0.1.3, but may not run with causalchamber==0.2.0.*

## Help & Feedback

If you encounter a bug, need help using the package, or want to leave us some (highly welcome) feedback, please send us an [email](mailto:juan@causalchamber.ai), leave a [GitHub issue](https://github.com/juangamella/causal-chamber-package/issues) or start a new [Discussion](https://github.com/juangamella/causal-chamber-package/discussions).

## License

The code in this repository is shared under the permissive [MIT license](https://opensource.org/license/mit/). A copy of can be found in [LICENSE.txt](LICENSE.txt).

## Contributing

Please [reach out](mailto:juan@causalchamber.ai) if you would like to contribute code to the project.

You can also contribute financially with a donation as a [Github sponsor](https://github.com/sponsors/juangamella).

[![Donate](https://img.shields.io/static/v1.svg?logo=Github%20Sponsors&label=donate&message=Github%20Sponsors&color=e874ff)](https://github.com/sponsors/juangamella)
