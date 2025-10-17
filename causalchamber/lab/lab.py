# MIT License

# Copyright (c) 2025 Causal Chamber GmbH

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

# Imports from this package
import lab.chamber
from causalchamber.lab.api import API

class Lab():


    def __init__(self, credentials_file, endpoint=None, verbose=1):
        """
        """
        self._API = API(credentials_file, endpoint)
        # This will check credentials by making a call to the API and
        # updating the Lab's info
        self.get_status(verbose=verbose)

    def get_status(self, verbose=1):
        """
        """
        pass

    def get_experiment(self, experiment_id, verbose=1):
        """
        """
        # GET experiments/:experiment_id/
        pass
    
    def get_experiments(self, verbose=1):
        """
        """
        # GET experiments/
        pass
    
    def get_available_chambers(self, verbose=1):
        """
        """
        # GET users/:user_id
        pass

    def new_experiment(self, chamber_id, config):
        """
        """
        return Experiment(chamber_id, config, self.API)

    def __str__(self):
        pass

class Experiment(lab.chamber.Batch):


    def __init__(self, chamber_id, config, api):
        """
        """
        pass

    def submit(self):
        """
        """
        # POST /experiments
        pass

    # Everything else is inherited:
    
    @property
    def instructions(self):
        pass
    


    def clear(self):
        """
        """
        pass

    def set(self, verbose=1):
        """
        """
        pass

    def wait(self, verbose=1):
        """
        """
        pass

    def measure(self, chamber_id, config):
        """
        """
        pass

    def msr(self, chamber_id, config):
        """
        """
        pass
