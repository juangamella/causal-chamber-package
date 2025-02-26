__all__ = ["datasets", "utils", "ground_truth", "simulators"]

from . import datasets
from . import utils
from . import ground_truth
from . import simulators

citation = """
﻿@article{gamella2025chamber,
  author={Gamella, Juan L. and Peters, Jonas and B{\"u}hlmann, Peter},
  title={Causal chambers as a real-world physical testbed for {AI} methodology},
  journal={Nature Machine Intelligence},
  doi={10.1038/s42256-024-00964-x},
  year={2025},
}
"""

print(
    f"If you use our datasets or simulators for your work please consider citing:\n{citation}"
)
