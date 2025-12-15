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

"""
Module to access the Causal Chamber™ Remote Lab.
"""

# Standard library packages
import pathlib
import os
from datetime import datetime
import time
import numbers
import re

# Third-party packages
from termcolor import colored, cprint
import numpy as np
import pandas as pd
import yaml
from PIL import Image

# Imports from this package
from causalchamber.datasets.utils import download_and_extract
from causalchamber.lab.chamber import Batch
from causalchamber.lab.api import API
from causalchamber.lab.exceptions import LabError, UserError

class Lab():
    """
    Main interface for interacting with the Remote Lab.
    
    This class provides methods to
      - check chamber status
      - create, cancel and submit experiments to a chamber queue
      - download the data from completed experiments
      - open a real-time connection to a chamber
    """

    def __init__(self, credentials_file=None, endpoint="https://api.causalchamber.ai/v0", verbose=True, credentials=None):
        """Initialize the Lab interface.
        
        Parameters
        ----------
        credentials_file : str or None, optional
            Path to the configuration file containing API
            credentials. The file should contain the following lines:
            ```
            [api_keys]
            user = <YOUR USERNAME>
            password = <YOUR PASSWORD>
            ```
            Either credentials or credentials_file must be
            provided. If both are, credentials is used.
        endpoint : str, optional
            Base URL for the API endpoint. Default is "https://api.causalchamber.ai/v0".
        verbose : bool, optional        
            If True (default), this will print tables with the status
            of the available chambers and the 10 latest experiments
            belonging to the user. If False, nothing is printed.
        credentials : tuple of string or None, optional        
            A tuple (<user>, <password>) with the user and password
            for the API. Either credentials or credentials_file
            must be provided. If both are, credentials is used.

        Raises
        ------
        UserError
            If the credentials are incorrect.
        LabError
            If no connection to the API can be established or an
            internal error ocurred on our side.

        """
        self._API = API(credentials_file=credentials_file,
                        endpoint=endpoint,
                        credentials=credentials)

        # Get available chambers & experiments
        print("\n\nChambers") if verbose else None
        _ = self.get_available_chambers(verbose=verbose)
        print("\n\nExperiments") if verbose else None
        _ = self.get_experiments(verbose=verbose, print_max=10)
        

    def get_queue(self, chamber_id, verbose=True, print_max=None):
        """Retrieve the experiments that are waiting in the queue of the
        given chamber.
        
        Parameters
        ----------
        chamber_id : str
            The unique identifier of the chamber.
        verbose : bool, optional       
            If True (default), this will print a table with the
            experiments in the queue, their position and the user to
            whom they belong.
        print_max : int or None, optional
            Maximum number of experiments to print (if
            verbose=True). If None, all queued experiments are
            printed. Default is None.
        
        Returns
        -------
        dict
            Dictionary containing the experiment details including
            status, chamber_id, config, user, submission time, and
            other metadata.

        Raises
        ------
        UserError
            If the credentials are incorrect, the given chamber_id does
            not exist, or the corresponding chamber is not in queue mode.        
        LabError
            If no connection to the API can be established or an
            internal error ocurred on our side.

        """
        response = self._API.make_request('GET', f'queues/{chamber_id}')
        experiments = response.json()['experiments']
        # Sort by queue position
        sorted_by_position = sorted(experiments, key=lambda x: x['position'], reverse=True)
        # Optionally, print list of experiments
        if verbose:
            _print_queue_table(sorted_by_position, chamber_id, print_max=print_max)
        # Return experiments
        return sorted_by_position
        
    def get_experiment(self, experiment_id):
        """
        Retrieve the details of a specific experiment.
        
        Parameters
        ----------
        experiment_id : str
            The unique identifier of the experiment.
        
        Returns
        -------
        dict
            Dictionary containing the experiment details including
            status, chamber_id, config, submission time, and other
            metadata.

        Raises
        ------
        UserError
            If the credentials are incorrect.
        LabError
            If no connection to the API can be established or an
            internal error ocurred on our side.
        """
        response = self._API.make_request('GET', f'experiments/{experiment_id}')
        return response.json()
    
    def get_experiments(self, verbose=True, print_max=None):
        """
        Retrieve a list of all your experiments.
        
        Parameters
        ----------
        verbose : bool, optional        
            If True (default), this will print a table with the
            experiments belonging to the user in the credentials
            file. If False, nothing is printed.
        print_max : int or None, optional
            Maximum number of experiments to print (if
            verbose=True). If None, all experiments belonging to the
            user are printed. Default is None.

        Raises
        ------
        TypeError
            If print_max is not an integer.
        ValueError
            If print_max is not an integer larger than zero.
        
        Returns
        -------
        list of dict
            List of dictionaries containing information about each
            experiment, sorted by submission time (newest first).

        """
        # Call API
        response = self._API.make_request('GET', 'experiments')
        experiments = response.json()['experiments']
        # Sort by submission time
        newest_first = sorted(experiments, key=lambda x: x['submitted_on'], reverse=True)
        # Optionally, print list of experiments
        if verbose:
            _print_experiment_table(newest_first, print_max=print_max)
        # Return experiments
        return newest_first
    
    def get_available_chambers(self, verbose=True):
        """
        Retrieve a list of the available chambers.
        
        Parameters
        ----------
        verbose : bool, optional
            If True (default), this will print a table with
            information about the available chambers.
        
        Returns
        -------
        list of dict
            List of dictionaries containing chamber_id, status, model,
            mode, and valid configurations of each chamber.
        
        """
        response = self._API.make_request('GET', 'chambers')
        chambers = response.json()['chambers']
        # Optionally, print list of chambers
        if verbose:
            _print_chamber_table(chambers)
        # Return list of chambers
        return chambers

    def new_experiment(self, chamber_id, config):
        """Create a new experiment protocol.
        
        Parameters
        ----------
        chamber_id : str
            The unique identifier of the chamber that should execute
            the experiment.
        config : str
            The name of the configuration the chamber should load to
            execute this experiment.
        
        Returns
        -------
        Protocol
            The lab.Protocol object that can be used to add instructions and submit
            the experiment.
        
        """
        # TODO: decide if checking chamber and config is done here
        return Protocol(chamber_id, config, self._API)

    def cancel_experiment(self, experiment_id):
        """
        Cancel a queued experiment.
        
        Parameters
        ----------
        experiment_id : str
            The unique identifier of the experiment to cancel.
        
        Returns
        -------
        dict
            Dictionary containing the updated experiment metadata.
        
        """
        response = self._API.make_request('POST', f'experiments/{experiment_id}/cancel')
        return response.json()

    def download_data(self, experiment_id, root, verbose=True):
        """
        Download data from a completed experiment.
        
        Parameters
        ----------
        experiment_id : str
            The unique identifier of the experiment.
        root : str or pathlib.Path
            Directory where the data will be downloaded and extracted.
        verbose : bool, optional
            If True, traces are printed and a download progress bar is
            shown. If False no outputs are produced. Defauls to True.
        
        Returns
        -------
        pandas.DataFrame
            DataFrame containing the experimental observations.
        
        Raises
        ------
        UserError
            If the experiment is not in 'DONE' status.

        """
        experiment = self.get_experiment(experiment_id)
        current_status = experiment['status']
        if current_status != 'DONE':
            raise UserError(code = 0,
                            message = f"Experiment '{experiment_id}' is not finished yet (current status = {current_status})",
                            scheduler_id = experiment['scheduler_id'])
        else:
            dataset = ExperimentDataset(experiment_id = experiment_id,
                                        download_url = experiment['download_url'],
                                        checksum = experiment['checksum'],
                                        root = root,
                                        verbose=verbose)
            return dataset
        
class Protocol(Batch):
    """
    Object representing an experiment protocol, i.e., collection of
    instructions, that can be submitted to the queue.
    
    Attributes
    ----------
    chamber_id : str
        The unique identifier of the chamber that should execute the
        experiment.
    config : str
        The name of the configuration the chamber should load to
        execute this experiment.
    instructions : list of str
        The instructions in the protocol.
    """

    def __init__(self, chamber_id, config, api):
        """
        Initialize a new Protocol.
        
        Parameters
        ----------
        chamber_id : str
            The unique identifier of the chamber that should execute the
            experiment.
        config : str
            The name of the configuration the chamber should load to
            xexecute this experiment.
        api : lab.api.API
            The API client instance used for making requests.
        """
        # We purposefully overwrite the init method of lab.chamber.Batch
        self._chamber_id = chamber_id
        self._config = config
        self._API = api
        self._instructions = []

    @property
    def chamber_id(self):
        """
        Returns the chamber_id for this protocol.
        
        Returns
        -------
        str
            The unique identifier of the chamber that should execute the
            experiment.
        """
        return self._chamber_id

    @property
    def config(self):
        """
        Returns the chamber config for this protocol.
        
        Returns
        -------
        str
            The name of the configuration the chamber should load to
            execute this experiment.
        """
        return self._config
        
    def submit(self, tag=None):
        """Submit the protocol to the Lab for execution.
        
        Parameters
        ----------
        tag : str or None, optional
            Optional, user-defined string that can be used to help
            keep track of different experiments. Default is None.
        
        Returns
        -------
        experiment_id : str
            The unique identifier for the submitted experiment.
        
        Raises
        ------
        TypeError
            If tag is not a string or None.
        UserError
            If the protocol contains invalid / incorrect instructions
            for the given chamber & config, or if the user has reached
            the maximum number of experiments in the queue.
        LabError
            If no connection to the API can be established or an error
            on our side prevents submitting the experiment.

        """
        # POST /experiments
        body = {'chamber_id': self._chamber_id,
                'chamber_config': self._config,
                'instructions': self._instructions}
        if tag is not None and not isinstance(tag, str):
            raise TypeError(f"tag must be str, not {type(tag).__name__}")
        elif tag is not None:
            body['tag'] = tag
        response = self._API.make_request('POST', 'experiments', body)
        # Return the experiment id
        return response.json()['experiment_id']



class ExperimentDataset():
    """
    Container for experimental data downloaded from the Lab.    
    """

    def __init__(self, experiment_id, download_url, checksum, root, verbose=True):
        """
        Downloads the given experiment_id from the provided
        download_url into the directory specified in root. Verifies
        the downloaded file against the provided checksum.
        
        Parameters
        ----------
        experiment_id : str
            The unique identifier of the experiment.
        download_url : str
            URL to download the experiment data.
        checksum : str
            SHA256 checksum for data verification.
        root : str or pathlib.Path
            Root directory where the data will be stored.
        download : bool, optional
            Whether to download the data immediately. Default is True.
        verbose : bool, optional
            If True, a download progress bar is shown. If False no
            outputs are produced. Defauls to True.
        
        Raises
        ------
        FileNotFoundError
            If the root directory does not exist.
        """
        self._experiment_id = experiment_id
        self._download_url = download_url
        self._checksum = checksum
        self._root = pathlib.Path(root).resolve()
        if not os.path.isdir(self._root):
            raise FileNotFoundError(f"root directory '{self._root}' not found. Please check and try again.")
        # Download, verify and extract
        download_and_extract(url = self._download_url,
                             root=self._root,
                             checksum=self._checksum,
                             algorithm='sha256',
                             verbose=verbose)
        # Load the YAML metadata
        path_to_metadata = pathlib.Path(self._root, experiment_id, 'metadata.yaml')
        with open(path_to_metadata, 'r') as f:
            self.metadata = yaml.safe_load(f)
        # Store path to observations
        self._path_to_data = pathlib.Path(self._root, experiment_id, self.metadata['observations_file']).resolve()
        # Store path to images
        if self.metadata['image_directory'] is None:
            self._contains_images = False
        else:
            self._images_dir = pathlib.Path(self._root, experiment_id, self.metadata['image_directory'])
            self._contains_images = True

    @property
    def experiment_id(self):
        """
        Return the experiment_id of this dataset.

        Returns
        -------
        str
            The experiment id.        
        """
        return self._experiment_id
            
    @property
    def dataframe(self):
        """
        Get the experimental observations as a DataFrame.
        
        Returns
        -------
        pandas.DataFrame
            DataFrame containing the experimental observations.
        """
        return pd.read_csv(self._path_to_data)

    @property
    def image_arrays(self):
        """
        Load the experiment images from disk into a list of numpy.ndarray with dimensions (height, width, 3).

        For lazy loading, use image_iterator instead.
        
        Returns
        -------
        list of numpy.ndarray
            The a list of the experiment images as numpy arrays.

        Raises
        ------
        NotImplementedError
            If this is not an image dataset.

        """
        if not self._contains_images:
            raise NotImplementedError("This is not an image dataset!")
        n = self.metadata['n_observations']
        images = []
        for i in range(n):
            path_to_image = pathlib.Path(self._images_dir, f'image_{i+1}.jpeg')
            images.append(
                np.array(Image.open(path_to_image))
            )
        return images

    @property
    def image_iterator(self):
        """
        Return an iterator over the experiment images, which are numpy
        arrays of dimension (height, width, 3). Images are loaded
        lazily from disk only when requested.

        Returns
        ------
        numpy.ndarray
            Each image as a numpy array.

        Raises
        ------
        NotImplementedError
            If this is not an image dataset.

        """
        if not self._contains_images:
            raise NotImplementedError("This is not an image dataset!")

        n = self.metadata['n_observations']
        
        def _generate():
            for i in range(n):
                path_to_image = pathlib.Path(self._images_dir, f'image_{i+1}.jpeg')
                yield np.array(Image.open(path_to_image))

        return _generate()


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
    """
    Format a status string with the appropriate color.
    
    Parameters
    ----------
    status : str
        Status string to format (e.g., 'READY', 'RUNNING', 'DONE').
    
    Returns
    -------
    str
        Colored status string using ANSI escape codes.
    
    Examples
    --------
    >>> _fmt_status('DONE')
    'DONE'
    """
    return colored(status, _STATUS_COLORS.get(status, None))


def _fmt_timestamp(ts):
    """
    Transform an epoch timestamp into a human-readable datetime in the
    local timezone of the machine.
    
    Parameters
    ----------
    ts : float
        Epoch timestamp in seconds.
    
    Returns
    -------
    str
        Formatted datetime string, e.g., 'Fri, Feb 13, 2009 23:31:30 UTC'
    
    Examples
    --------
    >>> _fmt_timestamp(1761471966)
    'Sun, Oct 26, 2025 10:46:06 CET'

    """
    return datetime.fromtimestamp(ts).astimezone().strftime('%a, %b %d, %Y %H:%M:%S %Z')
    

def _strip_ansi(text):
    """
    Remove ANSI escape sequences from text for accurate length
    calculation. Used in the printing functions below.
    
    Parameters
    ----------
    text : str
        Input text.
    
    Returns
    -------
    str
        Output text with all ANSI escape sequences removed.
    
    Examples
    --------
    >>> colored_text = "\\x1b[32mGreen text\\x1b[0m"
    >>> plain_text = _strip_ansi(colored_text)
    >>> print(plain_text)
    Green text
    """
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_escape.sub('', str(text))

def _print_chamber_table(chambers, indentation=0, col_separator=' ', line_separator = '─', line_char = '─'):
    """
    Print a formatted table of chamber information.
    
    Parameters
    ----------
    chambers : list of dict
        List of dictionaries containing chamber information. Each dictionary
        should have keys: 'status', 'chamber_id', 'chamber_model', 'mode',
        and 'valid_configs'.
    indentation : int, optional
        Number of spaces to indent the table. Default is 0.
    col_separator : str, optional
        Character(s) to use as column separator. Default is ' '.
    line_separator : str, optional
        Character to use at line boundaries, including between columns. Default is '─'.
    line_char : str, optional
        Character to use for horizontal lines. Default is '─'.
    
    Returns
    -------
    None
        Prints the table to stdout.
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
            col_widths[i] = max(col_widths[i], len(_strip_ansi(value)))
    
    # Print header
    sep_with_space = f' {col_separator} '
    header_row = col_separator + ' ' + sep_with_space.join(h.ljust(w) for h, w in zip(headers, col_widths)) + ' ' + col_separator
    
    separator = line_separator + line_separator.join(line_char * (w + 2) for w in col_widths) + line_separator

    print()
    print(' ' * indentation + header_row)
    print(' ' * indentation + separator)
    
    # Print data rows
    for row in rows:
        # Calculate padding for each cell based on visible length
        padded_row = []
        for value, width in zip(row, col_widths):
            visible_len = len(_strip_ansi(value))
            padding_needed = width - visible_len
            padded_value = str(value) + ' ' * padding_needed
            padded_row.append(padded_value)
        
        row_str = col_separator + ' ' + sep_with_space.join(padded_row) + ' ' + col_separator
        print(' ' * indentation + row_str)
    
    print(' ' * indentation + separator)


def _print_experiment_table(experiments, print_max=None, indentation=0, col_separator=' ', line_separator = '─', line_char = '─'):
    """
    Print a formatted table of experiment information.
    
    Parameters
    ----------
    experiments : list of dict
        List of dictionaries containing experiment information. Each dictionary
        should have keys: 'status', 'tag', 'experiment_id', 'chamber_id',
        'config', and 'submitted_on'.
    print_max : int or None, optional
        Maximum number of experiments to print. If None, all experiments
        are printed. Default is None.
    indentation : int, optional
        Number of spaces to indent the table. Default is 0.
    col_separator : str, optional
        Character(s) to use as column separator. Default is ' '.
    line_separator : str, optional
        Character to use at line boundaries, including between columns. Default is '─'.
    line_char : str, optional
        Character to use for horizontal lines. Default is '─'.
    
    Returns
    -------
    None
        Prints the table to stdout.
    
    Raises
    ------
    TypeError
        If print_max is not an integer or None.
    ValueError
        If print_max is less than or equal to zero.
    
    Examples
    --------
    >>> experiments = [
    ...     {'status': 'DONE', 'tag': 'test1', 'experiment_id': 'exp_01',
    ...      'chamber_id': 'ch_01', 'config': 'config_A', 'submitted_on': 1234567890}
    ... ]
    >>> _print_experiment_table(experiments, print_max=10)
    <BLANKLINE>
      Status   Tag     Experiment ID   Chamber ID   Config     Submitted On                    
    ───────────────────────────────────────────────────────────────────────────────────────────
      DONE     test1   exp_01          ch_01        config_A   Sat, Feb 14, 2009 00:31:30 CET  
    ───────────────────────────────────────────────────────────────────────────────────────────
     Date/time in your machine's local timezone — current time = ...
    <BLANKLINE>
    
    >>> _print_experiment_table(experiments, print_max=10.5)
    Traceback (most recent call last):
        ...
    TypeError: print_max must be an integer or None, not float
    >>> _print_experiment_table(experiments, print_max=-1)
    Traceback (most recent call last):
        ...
    ValueError: print_max must be None or an integer larger than zero
    >>> _print_experiment_table(experiments, print_max='10')
    Traceback (most recent call last):
        ...
    TypeError: print_max must be an integer or None, not str
    >>> _print_experiment_table(experiments, print_max=0)
    Traceback (most recent call last):
        ...
    ValueError: print_max must be None or an integer larger than zero
    """
    # Check inputs
    if print_max is not None and not isinstance(print_max, numbers.Integral):
        raise TypeError(f"print_max must be an integer or None, not {type(print_max).__name__}")
    if print_max is not None and print_max <= 0:
        raise ValueError("print_max must be None or an integer larger than zero")

    # Print n experiments
    n = len(experiments) if print_max is None else min(print_max, len(experiments))
    to_print = experiments[0:n]
    
    # Default values for missing fields
    DEFAULT_VALUE = "NA"
    
    # Calculate column widths for better formatting
    headers = ["Status", "Tag", "Experiment ID", "Chamber ID", "Config", "Submitted On"]
    col_widths = [len(h) for h in headers]
    
    # Process data and calculate maximum widths
    rows = []
    for experiment in to_print:
        status = _fmt_status(experiment.get('status'))
        tag = experiment.get('tag', DEFAULT_VALUE)
        experiment_id = experiment.get('experiment_id', DEFAULT_VALUE)
        chamber_id = experiment.get('chamber_id', DEFAULT_VALUE)
        config = experiment.get('config', DEFAULT_VALUE)
        if 'submitted_on' in experiment:
            submitted_on = _fmt_timestamp(experiment.get('submitted_on'))
        else:
            submitted_on = DEFAULT_VALUE
        
        row = [status, tag, experiment_id, chamber_id, config, submitted_on]
        rows.append(row)
        
        # Update column widths (using stripped text for length calculation)
        for i, value in enumerate(row):
            col_widths[i] = max(col_widths[i], len(_strip_ansi(value)))
    
    # Print header
    sep_with_space = f' {col_separator} '
    header_row = col_separator + ' ' + sep_with_space.join(h.ljust(w) for h, w in zip(headers, col_widths)) + ' ' + col_separator

    separator = line_separator + line_separator.join(line_char * (w + 2) for w in col_widths) + line_separator
    
    print()
    print(' ' * indentation + header_row)
    print(' ' * indentation + separator)
    
    # Print data rows
    for row in rows:
        # Calculate padding for each cell based on visible length
        padded_row = []
        for value, width in zip(row, col_widths):
            visible_len = len(_strip_ansi(value))
            padding_needed = width - visible_len
            padded_value = str(value) + ' ' * padding_needed
            padded_row.append(padded_value)
        
        row_str = col_separator + ' ' + sep_with_space.join(padded_row) + ' ' + col_separator
        print(' ' * indentation + row_str)

    if len(to_print) < len(experiments):
        print()
        print(' ' * indentation, colored(f' --- showing {len(to_print)} / {len(experiments)} experiments ---', (100,100,100)))
    print(' ' * indentation + separator)
    print(' ' * indentation + f" Date/time in your machine's local timezone — current time = {_fmt_timestamp(time.time())}")
    print()


def _print_queue_table(experiments, chamber_id, print_max=None, indentation=0, col_separator=' ', line_separator = '─', line_char = '─'):
    """
    Print a formatted table of experiment information.
    
    Parameters
    ----------
    experiments : list of dict
        List of dictionaries containing experiment information. Each dictionary
        should have keys: 'status', 'tag', 'experiment_id', 'chamber_id',
        'config', and 'submitted_on'.
    print_max : int or None, optional
        Maximum number of experiments to print. If None, all experiments
        are printed. Default is None.
    indentation : int, optional
        Number of spaces to indent the table. Default is 0.
    col_separator : str, optional
        Character(s) to use as column separator. Default is ' '.
    line_separator : str, optional
        Character to use at line boundaries, including between columns. Default is '─'.
    line_char : str, optional
        Character to use for horizontal lines. Default is '─'.
    
    Returns
    -------
    None
        Prints the table to stdout.
    
    Raises
    ------
    TypeError
        If print_max is not an integer or None.
    ValueError
        If print_max is less than or equal to zero.
    
    Examples
    --------
    >>> _print_queue_table([], 'ch-abcd-xyzw', print_max=10)
    <BLANKLINE>
    Experiments in the queue for chamber 'ch-abcd-xyzw'. Order is by position, i.e., 1 = next to run
    <BLANKLINE>
         Status   Tag   Experiment ID   Submitted By   Submitted On  
    ─────────────────────────────────────────────────────────────────
             --- there are no experiments in the queue ---
    ─────────────────────────────────────────────────────────────────
     Date/time in your machine's local timezone — current time = ...
    <BLANKLINE>

    >>> experiments = [
    ...     {'status': 'QUEUED', 'tag': 'test1', 'experiment_id': 'exp_01',
    ...      'chamber_id': 'ch-abcd-xyzw', 'config': 'config_A', 'submitted_on': 1234567890, 'user_id': 'test@test', 'position': 1}
    ... ]
    >>> _print_queue_table(experiments, 'ch-abcd-xyzw', print_max=10)
    <BLANKLINE>
    Experiments in the queue for chamber 'ch-abcd-xyzw'. Order is by position, i.e., 1 = next to run
    <BLANKLINE>
          Status   Tag     Experiment ID   Submitted By   Submitted On                    
    ──────────────────────────────────────────────────────────────────────────────────────
      1   QUEUED   test1   exp_01          test@test      Sat, Feb 14, 2009 00:31:30 CET  
    ──────────────────────────────────────────────────────────────────────────────────────
     Date/time in your machine's local timezone — current time = ...
    <BLANKLINE>
    
    >>> _print_queue_table(experiments, 'ch-abcd-xyzw', print_max=10.5)
    Traceback (most recent call last):
        ...
    TypeError: print_max must be an integer or None, not float
    >>> _print_queue_table(experiments, 'ch-abcd-xyzw', print_max=-1)
    Traceback (most recent call last):
        ...
    ValueError: print_max must be None or an integer larger than zero
    >>> _print_queue_table(experiments, 'ch-abcd-xyzw', print_max='10')
    Traceback (most recent call last):
        ...
    TypeError: print_max must be an integer or None, not str
    >>> _print_queue_table(experiments, 'ch-abcd-xyzw', print_max=0)
    Traceback (most recent call last):
        ...
    ValueError: print_max must be None or an integer larger than zero
    """
    # Check inputs
    if print_max is not None and not isinstance(print_max, numbers.Integral):
        raise TypeError(f"print_max must be an integer or None, not {type(print_max).__name__}")
    if print_max is not None and print_max <= 0:
        raise ValueError("print_max must be None or an integer larger than zero")

    # Print n experiments
    n = len(experiments) if print_max is None else min(print_max, len(experiments))
    to_print = experiments[0:n]
    
    # Default values for missing fields
    DEFAULT_VALUE = "NA"
    
    # Calculate column widths for better formatting
    headers = ["", "Status", "Tag", "Experiment ID", "Submitted By", "Submitted On"]
    col_widths = [len(h) for h in headers]
    
    # Process data and calculate maximum widths
    rows = []
    for experiment in to_print:
        position = experiment.get('position', DEFAULT_VALUE)
        status = _fmt_status(experiment.get('status'))
        tag = experiment.get('tag', DEFAULT_VALUE)
        experiment_id = experiment.get('experiment_id', DEFAULT_VALUE)
        if 'submitted_on' in experiment:
            submitted_on = _fmt_timestamp(experiment.get('submitted_on'))
        else:
            submitted_on = DEFAULT_VALUE
        submitted_by = experiment.get('user_id', DEFAULT_VALUE)
        
        row = [position, status, tag, experiment_id, submitted_by, submitted_on]
        rows.append(row)
        
        # Update column widths (using stripped text for length calculation)
        for i, value in enumerate(row):
            col_widths[i] = max(col_widths[i], len(_strip_ansi(value)))
    
    # Print header
    sep_with_space = f' {col_separator} '
    header_row = col_separator + ' ' + sep_with_space.join(h.ljust(w) for h, w in zip(headers, col_widths)) + ' ' + col_separator

    separator = line_separator + line_separator.join(line_char * (w + 2) for w in col_widths) + line_separator

    print()
    print(f"Experiments in the queue for chamber '{chamber_id}'. Order is by position, i.e., 1 = next to run")
    print()
    print(' ' * indentation + header_row)
    print(' ' * indentation + separator)
    
    # Print data rows
    for row in rows:
        # Calculate padding for each cell based on visible length
        padded_row = []
        for value, width in zip(row, col_widths):
            visible_len = len(_strip_ansi(value))
            padding_needed = width - visible_len
            padded_value = str(value) + ' ' * padding_needed
            padded_row.append(padded_value)
        
        row_str = col_separator + ' ' + sep_with_space.join(padded_row) + ' ' + col_separator
        print(' ' * indentation + row_str)

    if len(to_print) < len(experiments):
        print()
        print(' ' * indentation, colored(f' --- showing {len(to_print)} / {len(experiments)} experiments ---', (100,100,100)))
    if len(to_print) == 0:
        print(' ' * indentation, colored(f'        --- there are no experiments in the queue ---', (100,100,100)))
    print(' ' * indentation + separator)
    print(' ' * indentation + f" Date/time in your machine's local timezone — current time = {_fmt_timestamp(time.time())}")
    print()


# ----------------------------------------------------------------------
# Doctests

if __name__ == "__main__":
    import doctest
    doctest.testmod(
        extraglobs={},
        verbose=True,
        optionflags=doctest.ELLIPSIS,
    )
