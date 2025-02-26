# [DEPRECATED] Mechanistic Models: Python Implementation

<mark>**NOTICE:** These models (except E1) are now implemented as simulators in the [Simulator Repository](https://github.com/juangamella/causal-chamber-package/tree/main/causalchamber/simulators). Please use that implementation instead.</mark>

Here we provide the original Python implementations of the mechanistic models described in [Appendix IV](https://arxiv.org/pdf/2404.11341#page=28&zoom=100,57,65) of the original [paper](https://www.nature.com/articles/s42256-024-00964-x). The models follow the same nomenclature as in the paper, e.g., to import and run model A1 of the steady-state fan speed:
```Python
import numpy as np
from causalchamber.models import model_a1
model_a1(L=np.linspace(0,1,10), L_min=0.1, omega_max=314.15)

# Output:

# array([ 31.415     ,  34.90555556,  69.81111111, 104.71666667,
#        139.62222222, 174.52777778, 209.43333333, 244.33888889,
#        279.24444444, 314.15      ])
```

The code is organized as follows:

- [`wind_tunnel_models.py`](wind_tunnel_models.py) contains models A1, A2, B1, C1, C2 and C3
- [`wind_tunnel_simulators.py`](wind_tunnel_simulators.py) contains the simulators of fan speeds and air pressure showin in shown in [Fig. 6f](https://www.nature.com/articles/s42256-024-00964-x/figures/6) of the [paper](https://www.nature.com/articles/s42256-024-00964-x).
- [`light_tunnel_models.py`](light_tunnel_models.py) contains model E1
- [`image_capture.py`](image_capture.py) contains models F1, F2 and F3 of the image capture process (output shown in [Fig. 6f](https://www.nature.com/articles/s42256-024-00964-x/figures/6) of the [paper](https://www.nature.com/articles/s42256-024-00964-x)).

Model D1 of the difference between the readings of the up- and downwind barometers is not implemented and is used only as a ground-truth for the symbolic regression task shown in [Fig. 6e](https://www.nature.com/articles/s42256-024-00964-x/figures/6) of the [paper](https://www.nature.com/articles/s42256-024-00964-x).

If you use the models in your scientific work, please consider citing:

```
﻿@article{gamella2025chamber,
  author={Gamella, Juan L. and Peters, Jonas and B{\"u}hlmann, Peter},
  title={Causal chambers as a real-world physical testbed for {AI} methodology},
  journal={Nature Machine Intelligence},
  doi={10.1038/s42256-024-00964-x},
  year={2025},
}
```
