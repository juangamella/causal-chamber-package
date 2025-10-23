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

# Standard library packages
import pathlib
import os

# Third-party packages
from termcolor import colored, cprint
import pandas as pd
import yaml

# Imports from this package
from causalchamber.datasets.utils import download_and_extract
from causalchamber.lab.chamber import Batch
from causalchamber.lab.api import API
from causalchamber.lab.exceptions import LabError, UserError

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
        return Protocol(chamber_id, config, self._API)

    def cancel_experiment(self, experiment_id):
        response = self._API.make_request('POST', f'experiments/{experiment_id}/cancel')
        return response.json()

    def download_data(self, experiment_id, root):
        experiment = self.get_experiment(experiment_id, verbose=0)
        current_status = experiment['status']
        if current_status != 'DONE':
            raise UserError(0, f"Experiment '{experiment_id}' is not finished yet (current status = {current_status})")
        else:
            dataset = ExperimentDataset(experiment_id = experiment_id,
                                        download_url = experiment['download_url'],
                                        checksum = experiment['checksum'],
                                        root = root)
            return dataset.data
        
    def __str__(self):
        pass

class Protocol(Batch):

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



class ExperimentDataset():

    def __init__(self, experiment_id, download_url, checksum, root, download=True):
        self._download_url = download_url
        self._checksum = checksum
        self._root = root# pathlib.Path(root).resolve()
        if not os.path.isdir(self._root):
            raise FileNotFoundError(f"root directory '{self._root}' not found. Please check and try again.")
        # Download, verify and extract
        if download:
            download_and_extract(url = self._download_url,
                                 root=self._root,
                                 checksum=self._checksum,
                                 algorithm='sha256')
        # Load the YAML and data
        path_to_metadata = pathlib.Path(root, experiment_id, 'metadata.yaml')
        with open(path_to_metadata, 'r') as f:
            metadata = yaml.safe_load(f)
        # Store path to observations
        self._path_to_data = pathlib.Path(root, experiment_id, metadata['observations_file']).resolve()
        # Store path to images
        if metadata['image_directory'] is None:
            self._contains_images = False
        else:
            self._images_dir = pathlib.Path(root, experiment_id, metadata['image_directory'])
            self._contains_images = True

    @property
    def data(self):
        return pd.read_csv(self._path_to_data)

    @property
    def images(self):
        # TODO
        raise NotImplementedError()


# --------------------------------------------------------------------
# Auxiliary functions

_STATUS_COLORS = {
    # Chamber status
    'READY': 'light_green',
    'LOADING': 'light_cyan', 
    'EXECUTING': 'light_cyan',
    'ERROR': 'light_red',
    'OFFLINE': 'light_red',
    # Experiment status
    'QUEUED': 'yellow',
    'RUNNING': 'green',
    'FAILED': 'light_red',
    'CANCELED': (150,150,150),
    'DONE': 'light_green'
    }

def _fmt_status(status):
    return colored(status, _STATUS_COLORS.get(status, None))

import re

def strip_ansi(text):
    """Remove ANSI escape sequences from text for accurate length calculation"""
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_escape.sub('', str(text))

def _print_chamber_table(chambers, indentation=0, col_separator=' '):
    """
    Print a formatted table from a list of chamber dictionaries.
    
    Args:
        chambers: List of dictionaries containing chamber information
        indentation: Number of spaces to indent the table (default: 0)
        col_separator: Character(s) to use as column separator (default: '|')
    """
    # Default values for missing fields
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
    sep_with_space = f' {col_separator} '
    header_row = col_separator + ' ' + sep_with_space.join(h.ljust(w) for h, w in zip(headers, col_widths)) + ' ' + col_separator
    
    separator = '+' + '+'.join('-' * (w + 2) for w in col_widths) + '+'
    # # Create separator line based on separator type
    # if col_separator == '|':
    #     separator = '+' + '+'.join('-' * (w + 2) for w in col_widths) + '+'
    # else:
    #     # For other separators, use a simple line
    #     total_width = sum(col_widths) + len(col_widths) * 3 + 1
    #     separator = '-' * total_width
    
    # print(' ' * indentation + separator)
    print()
    print(' ' * indentation + header_row)
    print(' ' * indentation + separator)
    
    # Print data rows
    for row in rows:
        # Calculate padding for each cell based on visible length
        padded_row = []
        for value, width in zip(row, col_widths):
            visible_len = len(strip_ansi(value))
            padding_needed = width - visible_len
            padded_value = str(value) + ' ' * padding_needed
            padded_row.append(padded_value)
        
        row_str = col_separator + ' ' + sep_with_space.join(padded_row) + ' ' + col_separator
        print(' ' * indentation + row_str)
    
    print(' ' * indentation + separator)


def _print_experiment_table(experiments, indentation=0, col_separator=' '):
    """
    Print a formatted table from a list of experiment dictionaries.
    
    Args:
        experiments: List of dictionaries containing experiment information
        indentation: Number of spaces to indent the table (default: 0)
        col_separator: Character(s) to use as column separator (default: '|')
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
        download_url = experiment.get('download_url', DEFAULT_VALUE)
        
        row = [status, tag, experiment_id, chamber_id, config, submitted_on]
        rows.append(row)
        
        # Update column widths (using stripped text for length calculation)
        for i, value in enumerate(row):
            col_widths[i] = max(col_widths[i], len(strip_ansi(value)))
    
    # Print header
    sep_with_space = f' {col_separator} '
    header_row = col_separator + ' ' + sep_with_space.join(h.ljust(w) for h, w in zip(headers, col_widths)) + ' ' + col_separator

    separator = '+' + '+'.join('-' * (w + 2) for w in col_widths) + '+'
    # # Create separator line based on separator type
    # if col_separator == '|':
    #     separator = '+' + '+'.join('-' * (w + 2) for w in col_widths) + '+'
    # else:
    #     # For other separators, use a simple line
    #     total_width = sum(col_widths) + len(col_widths) * 3 + 1
    #     separator = '-' * total_width
    
    # print(' ' * indentation + separator)
    print()
    print(' ' * indentation + header_row)
    print(' ' * indentation + separator)
    
    # Print data rows
    for row in rows:
        # Calculate padding for each cell based on visible length
        padded_row = []
        for value, width in zip(row, col_widths):
            visible_len = len(strip_ansi(value))
            padding_needed = width - visible_len
            padded_value = str(value) + ' ' * padding_needed
            padded_row.append(padded_value)
        
        row_str = col_separator + ' ' + sep_with_space.join(padded_row) + ' ' + col_separator
        print(' ' * indentation + row_str)
    
    print(' ' * indentation + separator)
