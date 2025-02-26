# MIT License

# Copyright (c) 2025 Juan L Gamella

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

# Run the scripts generated from the tutorial notebooks
test-scripts: venv-test scripts
	( \
	. venv-test/bin/activate; \
	python test_scripts/tutorial_DecoderSimple.py && \
	python test_scripts/tutorial_Deterministic.py && \
	python test_scripts/tutorial_ModelsF.py && \
	python test_scripts/tutorial_ModelsAB.py \
    )

scripts:
	jupyter nbconvert --to script tutorial_DecoderSimple.ipynb --output-dir=test_scripts
	jupyter nbconvert --to script tutorial_Deterministic.ipynb --output-dir=test_scripts
	jupyter nbconvert --to script tutorial_ModelsF.ipynb --output-dir=test_scripts
	jupyter nbconvert --to script tutorial_ModelsAB.ipynb --output-dir=test_scripts

# Set up virtual environment
venv-test: requirements.txt
	python3 -m venv ./venv-test
	( \
	. venv-test/bin/activate; \
	pip install --upgrade pip setuptools; \
	pip install -r test_scripts/requirements.txt; \
	)

clean:
	rm -rf venv-test

.PHONY: venv-test, clean
