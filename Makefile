# MIT License

# Copyright (c) 2024 Juan L. Gamella

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

SUITE = all

# Run tests
tests: examples doctests simulator-tutorials test-downloads unit-tests

test-downloads:
	python -m unittest causalchamber.test.test_downloads

# Run the doctests
doctests:
	PYTHONPATH=./ python causalchamber/datasets/main.py
	PYTHONPATH=./ python causalchamber/ground_truth/main.py
	PYTHONPATH=./ python causalchamber/lab/api.py
	PYTHONPATH=./ python causalchamber/lab/chamber.py
	PYTHONPATH=./ python causalchamber/lab/lab.py


# Run the examples from the README
examples:
	# PYTHONPATH=./ python examples/example_readme_queue.py
	# PYTHONPATH=./ python examples/example_readme_rt.py
	PYTHONPATH=./ python examples/examples_readme_datasets_gt_models.py

# Run the sctipts for the simulator tutorials
simulator-tutorials:
	( \
	cd causalchamber/simulators/tutorials/; \
	make test-scripts; \
    )

# Run the unit tests

unit-tests:
ifeq ($(SUITE),all)
	python -m unittest discover causalchamber.lab.test
else
	python -m unittest $(SUITE)
endif


# Make a virtual environment with the package's dependencies
venv:
	python3 -m venv ./venv
	( \
	. venv/bin/activate; \
	pip install --upgrade pip setuptools; \
	pip install numpy pandas requests pyyaml termcolor Pillow tqdm \
	)


.PHONY: test, tests, doctests, examples
