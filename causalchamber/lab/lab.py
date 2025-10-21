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

# Third-party packages
from termcolor import colored, cprint

# Imports from this package
from causalchamber.lab.chamber import Batch
from causalchamber.lab.api import API

class Lab():

    def __init__(self, credentials_file, endpoint="https://api.causalchamber.ai/v0", verbose=1):
        """
        """
        self._API = API(credentials_file, endpoint)        
        self.get_status(verbose=verbose) # This checks credentials by making a call to the API and
        # updating the Lab's info

    def get_status(self, verbose=1):
        """
        """
        pass

    def get_experiment(self, experiment_id, verbose=1):
        """
        """
        response = self._API.make_request('GET', f'experiments/{experiment_id}')
        experiment = response.json()
        # Optionally, print list of experiments
        if verbose:
            pass
        # Return experiments
        return experiment
    
    def get_experiments(self, verbose=1):
        """
        """
        response = self._API.make_request('GET', 'experiments')
        experiments = response.json()['experiments']
        # Optionally, print list of experiments
        if verbose:
            _print_experiment_table(experiments)
        # Return experiments
        return experiments
    
    def get_available_chambers(self, verbose=1):
        """
        """
        response = self._API.make_request('GET', 'chambers')
        chambers = response.json()['chambers']
        # Optionally, print list of chambers
        if verbose:
            _print_chamber_table(chambers)
        # Return list of chambers
        return chambers

    def new_experiment(self, chamber_id, config):
        """
        """
        # TODO: decide if checking chamber and config is done here
        return Experiment(chamber_id, config, self._API)

    def cancel_experiment(self, experiment_id):
        response = self._API.make_request('POST', f'experiments/{experiment_id}/cancel')
        return response.json()

    def download_data(self, experiment_id, root):
        # Write following causalchamber.datasets.main.Dataset
        pass
    
    def __str__(self):
        pass

class Experiment(Batch):


    def __init__(self, chamber_id, config, api, verbose=1):
        """
        """
        self._chamber_id = chamber_id
        self._config = config
        self._API = api
        self._instructions = []
        self.verbose = verbose

    @property
    def chamber_id(self):
        return self._chamber_id

    @property
    def config(self):
        return self._config
        
    def submit(self, tag=None):
        """
        """
        # POST /experiments
        body = {'chamber_id': self._chamber_id,
                'chamber_config': self._config,
                'instructions': self._instructions}
        if tag is not None and not isinstance(tag, str):
            raise TypeError(f"tag must be str, not {type(user_id).__name__}")
        elif tag is not None:
            body['tag'] = tag
        response = self._API.make_request('POST', 'experiments', body)
        # Return the experiment id
        return response.json()['experiment_id']


# --------------------------------------------------------------------
# Auxiliary functions

_STATUS_COLORS = {
    # Chamber status
    'READY': 'light_green',
    'LOADING': 'light_cyan', 
    'EXECUTING': 'light_cyan',
    'ERROR': 'red',
    'OFFLINE': 'red',
    # Experiment status
    'QUEUED': (255,176,0),
    'RUNNING': (120,94,240),
    'FAILED': (254,97,0),
    'CANCELED': (150,150,150),
    'DONE': (120,94,240)
    }

def _fmt_status(status):
    return colored(status, _STATUS_COLORS.get(status, None))

import re

def strip_ansi(text):
    """Remove ANSI escape sequences from text for accurate length calculation"""
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_escape.sub('', str(text))

def _print_chamber_table(chambers):
    """
    Print a formatted table from a list of chamber dictionaries.
    
    Args:
        chambers: List of dictionaries containing chamber information
    """
    # Default values for missing fields
    DEFAULT_ENTRY = "NA"
    DEFAULT_ENTRY = "NA"
    
    # Calculate column widths for better formatting
    headers = ["Status", "Chamber ID", "Model", "Mode", "Valid Configurations"]
    col_widths = [len(h) for h in headers]
    
    # Process data and calculate maximum widths
    rows = []
    for chamber in chambers:
        status = _fmt_status(chamber.get('status'))
        chamber_id = chamber.get('chamber_id', '')
        model = chamber.get('chamber_model', DEFAULT_ENTRY)
        mode = chamber.get('mode', None)
        if mode is None:
            mode = DEFAULT_ENTRY
        
        # Handle valid_configs - it's a list of strings
        valid_configs = chamber.get('valid_configs', DEFAULT_ENTRY)
        if isinstance(valid_configs, list):
            valid_configs_str = ', '.join(f"'{config}'" for config in valid_configs)
        else:
            valid_configs_str = str(valid_configs)
        
        row = [status, chamber_id, model, mode, valid_configs_str]
        rows.append(row)
        
        # Update column widths (using stripped text for length calculation)
        for i, value in enumerate(row):
            col_widths[i] = max(col_widths[i], len(strip_ansi(value)))
    
    # Print header
    header_row = '| ' + ' | '.join(h.ljust(w) for h, w in zip(headers, col_widths)) + ' |'
    separator = '+' + '+'.join('-' * (w + 2) for w in col_widths) + '+'
    
    print(separator)
    print(header_row)
    print(separator)
    
    # Print data rows
    for row in rows:
        # Calculate padding for each cell based on visible length
        padded_row = []
        for value, width in zip(row, col_widths):
            visible_len = len(strip_ansi(value))
            padding_needed = width - visible_len
            padded_value = str(value) + ' ' * padding_needed
            padded_row.append(padded_value)
        
        row_str = '| ' + ' | '.join(padded_row) + ' |'
        print(row_str)
    
    print(separator)


def _print_experiment_table(experiments):
    """
    Print a formatted table from a list of experiment dictionaries.
    
    Args:
        experiments: List of dictionaries containing experiment information
    """
    # Default values for missing fields
    DEFAULT_VALUE = "NA"
    
    # Calculate column widths for better formatting
    headers = ["Status", "Tag", "Experiment ID", "Chamber ID", "Config", "Submitted On"]
    col_widths = [len(h) for h in headers]
    
    # Process data and calculate maximum widths
    rows = []
    for experiment in experiments:
        status = _fmt_status(experiment.get('status'))
        tag = experiment.get('tag', DEFAULT_VALUE)
        experiment_id = experiment.get('experiment_id', DEFAULT_VALUE)
        chamber_id = experiment.get('chamber_id', DEFAULT_VALUE)
        config = experiment.get('config', DEFAULT_VALUE)
        submitted_on = experiment.get('submitted_on', DEFAULT_VALUE)
        
        row = [status, tag, experiment_id, chamber_id, config, submitted_on]
        rows.append(row)
        
        # Update column widths (using stripped text for length calculation)
        for i, value in enumerate(row):
            col_widths[i] = max(col_widths[i], len(strip_ansi(value)))
    
    # Print header
    header_row = '| ' + ' | '.join(h.ljust(w) for h, w in zip(headers, col_widths)) + ' |'
    separator = '+' + '+'.join('-' * (w + 2) for w in col_widths) + '+'
    
    print(separator)
    print(header_row)
    print(separator)
    
    # Print data rows
    for row in rows:
        # Calculate padding for each cell based on visible length
        padded_row = []
        for value, width in zip(row, col_widths):
            visible_len = len(strip_ansi(value))
            padding_needed = width - visible_len
            padded_value = str(value) + ' ' * padding_needed
            padded_row.append(padded_value)
        
        row_str = '| ' + ' | '.join(padded_row) + ' |'
        print(row_str)
    
    print(separator)
