# `causalchamber`: Simulator Repository

[![PyPI version](https://badge.fury.io/py/causalchamber.svg)](https://badge.fury.io/py/causalchamber)
[![Downloads](https://static.pepy.tech/badge/causalchamber)](https://pepy.tech/project/causalchamber)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Donate](https://img.shields.io/static/v1.svg?logo=Github%20Sponsors&label=donate&message=Github%20Sponsors&color=e874ff)](https://github.com/sponsors/juangamella)

![The Causal Chambers: (left) the wind tunnel, and (right) the light tunnel with the front panel removed to show its interior.](https://causalchamber.s3.eu-central-1.amazonaws.com/downloadables/the_chambers.jpg)

The `causalchamber` package also provides Python implementations of simulators that model different physical phenomena in the causal chambers. The available simulators are indexed in this page, together with Jupyter notebooks with examples on how to use them. Some of the simulators were developed as part of scientific work; please consider citing the relevant papers if you use the simulators (see [References](#references) below).

The mechanistic models described in [Appendix IV](https://arxiv.org/pdf/2404.11341#page=28&zoom=100,57,65) of the original [paper](https://www.nature.com/articles/s42256-024-00964-x) have been refactored into simulators below, following the same nomenclature of the paper (e.g., ModelA1). For reproducibility, the original (and deprecated!) Python implementations provided in the paper are still available [here](../models).

## Simulator index

For each simulator, we specify the chamber and the [configurations](https://www.nature.com/articles/s42256-024-00964-x/figures/3) that it applies to, its additional dependencies (see below), a tutorial using a Jupyter notebook, and which paper should be cited if used (see [References](#references) below).

You can access the source code of each simulator by clicking on its name, e.g., [`lt.DecoderSimple`](lt/image/decoder.py).

### Dependencies

Some simulators may require additional dependencies, such as PyTorch. These are indicated for each simulator below under "Dependencies", and are included as optional dependencies for the package. For example, for the simulator [`lt.DecoderSimple`](#ltdecodersimple), the dependency `[torch]` indicates that the `causalchamber` package should be installed with the corresponding optional dependencies, as

```
pip install causalchamber[torch]
```

---
### [`lt.DecoderSimple`](lt/image/decoder.py)

| Chamber      | Config.  | Tutorial                                           | Dependencies | Cite               |
|:------------:|:--------:|:--------------------------------------------------:|:------------:|:------------------:|
| Light tunnel | `camera` | [notebook](tutorials/tutorial_DecoderSimple.ipynb) | `[torch]`    | [[2]](#references) |

<img src="https://causalchamber.s3.eu-central-1.amazonaws.com/downloadables/sim_images.png" alt="Simulated vs. real images collected from the light tunnel" width="600"/>

A deterministic simulator consisting of a multi-layer perceptron trained to generate synthetic images given the light source color ($R,G,B$) and polarizer angles ($\theta_1, \theta_2$). The output is a 64x64 px synthetic image. By default, the code downloads and uses a pre-trained model. See this [notebook](tutorials/decoder_training.ipynb) for the training details. Further details about the simulator and its training can be found in [Appendix C](TODO) of [[2]](#references).

---
### [`lt.ModelF1`](lt/image/models_f.py), [`lt.ModelF2`](lt/image/models_f.py), and [`lt.ModelF3`](lt/image/models_f.py)

| Chamber      | Config.  | Tutorial                                     | Dependencies | Cite               |
|:------------:|:--------:|:--------------------------------------------:|:------------:|:------------------:|
| Light tunnel | `camera` | [notebook](tutorials/tutorial_ModelsF.ipynb) | —            | [[1]](#references) |

<img src="https://causalchamber.s3.eu-central-1.amazonaws.com/downloadables/models_f13_outputs.png" alt="Simulated vs. real images collected from the light tunnel" width="600"/>

A family of simple, deterministic simulators that produce crude synthetic images given the light-source color ($R,G,B$) and polarizer positions ($\theta_1, \theta_2$). The synthetic images consist of a colored hexagon over a black background; the simulators differ in how the color of the hexagon is calculated, with a larger number (e.g., F3) indicating a more complex and accurate model, as shown in the above figure. The simulators are described in detail in [Appendix IV.2.2](https://arxiv.org/pdf/2404.11341#page=32&zoom=100,57,670) of [[1]](#references).

---
### [`lt.Deterministic`](lt/sensors/main.py)

| Chamber      | Config.             | Tutorial                                           | Dependencies | Cite               |
|:------------:|:-------------------:|:--------------------------------------------------:|:------------:|:------------------:|
| Light tunnel | `camera`,`standard` | [notebook](tutorials/tutorial_Deterministic.ipynb) | —            | [[2]](#references) |

<img src="https://causalchamber.s3.eu-central-1.amazonaws.com/downloadables/sim_sensors.png" alt="Simulated vs. real sensor measurements" width="450"/>

A deterministic simulator of the light tunnel, which models the response of the current ($\tilde{C}$), light-intensity ($\tilde{I}_1, \tilde{I}_2, \tilde{I}_3, \tilde{V}_1, \tilde{V}_2, \tilde{V}_3$) and angle ($\tilde{\theta}_1, \tilde{\theta}_2$) sensors as a function of the light source color ($R,G,B$), polarizer positions ($\theta_1, \theta_2$) and the parameters that control sensor behaviour. The simulator, its variables and its derivation are described in detail in [Appendix C](TODO) of [[2]](#references).

---
### [`wt.ModelA1`](wt/main.py), [`wt.ModelA2`](wt/main.py), and [`wt.ModelB1`](wt/main.py)

| Chamber     | Config.                       | Tutorial                                      | Dependencies | Cite               |
|:-----------:|:-----------------------------:|:---------------------------------------------:|:------------:|:------------------:|
| Wind tunnel | `standard`,`pressure-control` | [notebook](tutorials/tutorial_ModelsAB.ipynb) | —            | [[1]](#references) |


<img src="https://causalchamber.s3.eu-central-1.amazonaws.com/downloadables/wt_models.png" alt="Simulated vs. real sensor measurements of the wind tunnel" width="750"/>

Deterministic simulators of the fan speed ($\tilde{\omega}\_\text{in}, \tilde{\omega}\_\text{out}$, models A1 and A2) and current ($\tilde{C}\_\text{in}, \tilde{C}\_\text{out}$, model B1) as a function of the fan load ($L_\text{in}, L_\text{out}$). The simulators and their derivation are described in detail in [Appendix IV.1](https://arxiv.org/pdf/2404.11341#page=28&zoom=100,57,332) of [[1]](#references).

---
### [`wt.SimA1C2`](wt/main.py), [`wt.SimA1C3`](wt/main.py), and [`wt.SimA2C3`](wt/main.py)

| Chamber     | Config.                       | Tutorial         | Dependencies | Cite               |
|:-----------:|:-----------------------------:|:----------------:|:------------:|:------------------:|
| Wind tunnel | `standard`,`pressure-control` | [notebook](https://github.com/juangamella/causal-chamber-package_internal/blob/main/causalchamber/simulators/tutorials/tutorial_SimsAXCX.ipynb) | —            | [[1]](#references) |

<img src="https://causalchamber.s3.eu-central-1.amazonaws.com/downloadables/wt_simulators.png" alt="Simulated vs. real sensor measurements of the wind tunnel" width="550"/>

Stochastic simulators of the wind-tunnel pressure ($\tilde{P}\_\text{dw}$) as a function of the fan loads ($L\_\text{in}, L\_\text{out}$) and hatch position ($H$). Further details and the derivation of the simulators can be found in [Appendix IV.1](https://arxiv.org/pdf/2404.11341#page=28&zoom=100,57,332) of [[1]](#references).


## References

**[1] Causal chambers as a real-world physical testbed for AI methodology (2025)**

By Juan L. Gamella, Jonas Peters and Peter Bühlmann.

> [PDF](https://rdcu.be/d6kVj)

If you use the corresponding simulators in your scientific work, please consider citing:

```
﻿@article{gamella2025chamber,
  author={Gamella, Juan L. and Peters, Jonas and B{\"u}hlmann, Peter},
  title={Causal chambers as a real-world physical testbed for {AI} methodology},
  journal={Nature Machine Intelligence},
  doi={10.1038/s42256-024-00964-x},
  year={2025},
}
```

**[2] Sanity Checking Causal Representation Learning on a Simple Real-World System (2025)**

By Juan L. Gamella\*, Simon Bing\* and Jakob Runge (* = equal contribution).

> [PDF](https://rdcu.be/d6kVj)

If you use the corresponding simulators in your scientific work, please consider citing:

```
@article{gamellabing2025sanity,
  title     = {Sanity Checking Causal Representation Learning on a Simple Real-World System},
  author    = {Gamella*, Juan L. and Bing*, Simon and Runge, Jakob},
  year      = {2025},
  journal   = {arXiv preprint arXiv:TODO},
  note      = {*equal contribution}
}
```

## License

The code in this repository is shared open-source under the permissive [MIT license](https://opensource.org/license/mit/). A copy of can be found in [LICENSE.txt](../../LICENSE.txt).

## Contributing

Please [reach out](mailto:juan@causalchamber.ai) if you would like to contribute a simulator to this repository!

You can also contribute financially with a donation as a [Github sponsor](https://github.com/sponsors/juangamella).

[![Donate](https://img.shields.io/static/v1.svg?logo=Github%20Sponsors&label=donate&message=Github%20Sponsors&color=e874ff)](https://github.com/sponsors/juangamella)
