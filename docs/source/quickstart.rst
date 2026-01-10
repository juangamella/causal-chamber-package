Quick Start
===========

This guide will help you get started with the ``causalchamber`` package.

Remote Lab API
--------------

You can use the Remote Lab API to collect your own data from the chambers and run experiments in real time.

.. note::

   You can request access to the API at https://forms.causalchamber.ai/lab

Real-time Connection
~~~~~~~~~~~~~~~~~~~~

You can open a real-time connection to a chamber to send instructions and collect data:

.. code-block:: python

   import causalchamber.lab as lab

   # Open a real-time connection
   chamber = lab.Chamber(
       chamber_id='lt-demo-x81a',
       config='camera_fast',
       credentials_file='.credentials'
   )

   # Turn on the light source and take one image
   chamber.set('red', 255)
   df, images = chamber.measure(n=1)

Using Batches
~~~~~~~~~~~~~

You can submit several instructions at once using a batch:

.. code-block:: python

   # Start a new batch
   batch = chamber.new_batch()

   # Add instructions
   batch.set('red', 128)
   batch.measure(n=1)  # Image 1: red
   batch.set('blue', 128)
   batch.measure(n=1)  # Image 2: purple
   batch.set('pol_1', 90)
   batch.measure(n=1)  # Image 3: crossed polarizers

   # Submit the batch and receive the data
   df, images = batch.submit()

Submitting Jobs to the Queue
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For long-running experiments, use the queue:

.. code-block:: python

   # Connect to the Remote Lab
   rlab = lab.Lab(credentials_file='.credentials')

   # Start a new protocol
   experiment = rlab.new_experiment(
       chamber_id='wt-demo-ch4lu',
       config='full'
   )

   # Add instructions to the protocol
   experiment.wait(7_000)  # Wait 7s for fan speed to stabilize
   experiment.measure(n=80)  # Measure base state
   experiment.set('load_in', 1.0)  # Turn intake fan to max
   experiment.measure(n=20)  # Measure impulse state
   experiment.set('load_in', 0.01)  # Idle intake fan
   experiment.measure(n=80)  # Measure base state

   # Submit the experiment
   experiment_id = experiment.submit(tag='demo-queue')

   # Check experiment status
   rlab.get_experiments(print_max=1)

   # Download data once complete
   dataset = rlab.download_data(experiment_id, root='/tmp')
   observations = dataset.dataframe

Datasets
--------

You can download existing datasets from the `dataset repository <https://github.com/juangamella/causal-chamber>`_ directly into your Python code:

.. code-block:: python

   import causalchamber.datasets as datasets

   # Download the dataset and store it in the current directory
   dataset = datasets.Dataset(
       name='lt_camera_test_v1',
       root='./',
       download=True
   )

   # Select an experiment and load the observations and images
   experiment = dataset.get_experiment(name='palette')
   observations = experiment.as_pandas_dataframe()
   images = experiment.as_image_array(size='200')

Listing Available Datasets
~~~~~~~~~~~~~~~~~~~~~~~~~~

To see all available datasets:

.. code-block:: python

   import causalchamber.datasets as datasets
   datasets.list_available()

The package refreshes its list of available datasets every time it's imported.
