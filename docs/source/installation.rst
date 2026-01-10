Installation
============

Requirements
------------

The ``causalchamber`` package requires Python 3.6 or later.

Install from PyPI
-----------------

You can install the package via pip:

.. code-block:: bash

   pip install causalchamber

Dependencies
------------

The package will automatically install the following dependencies:

- numpy >= 1.18.0
- pandas >= 1.2.1
- requests >= 2.23.0
- pyyaml >= 5.3.1
- termcolor
- Pillow
- tqdm

Optional Dependencies
---------------------

For PyTorch-based functionality, you can install the optional torch dependencies:

.. code-block:: bash

   pip install causalchamber[torch]
