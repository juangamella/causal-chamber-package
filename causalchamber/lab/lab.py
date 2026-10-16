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
Module to access the Causal Chamber® Remote Lab.
"""

# Standard library packages
import pathlib
import os
from datetime import datetime
import time
import numbers

# Third-party packages
from rich.console import Console, Group
from rich.measure import Measurement
from rich.text import Text
import numpy as np
import pandas as pd
import yaml
from PIL import Image

# Imports from this package
from causalchamber.lab.utils import download_and_extract
from causalchamber.lab.chamber import Batch
from causalchamber.lab.api import API
from causalchamber.lab.exceptions import LabError, UserError
from causalchamber import _is_interactive, _PROMPT, _CODE_STYLE
from causalchamber.lab.dashboard import print_dashboard

# --------------------------------------------------------------------
# Login

_ENV_USER = "CAUSALCHAMBER_USER"
_ENV_PASSWORD = "CAUSALCHAMBER_PASSWORD"
_SIGNUP = "forms.causalchamber.ai/signup"
_REGEN = "forms.causalchamber.ai/regen"

# Instructions shown when no credentials are found, as rich markup
# (printed formatted in interactive sessions, as plain text otherwise)
_LOGIN_HELP = f"""\
Please provide your credentials in one of the following ways.

[bold]Credentials file[/bold]

  Pass the path to your credentials file

    {_PROMPT} [{_CODE_STYLE}]rlab = lab.login(credentials_file=[/][dim]"path/to/credentials_file"[/dim][{_CODE_STYLE}])[/]

  where the file contains the lines

    [dim]\\[api_keys]
    user = <user>
    password = <password>[/dim]

[bold]Environment variables[/bold]

  Set [dim]{_ENV_USER}[/dim] and [dim]{_ENV_PASSWORD}[/dim] before
  starting Python or Jupyter, e.g.,

    [dim]export {_ENV_USER}=<user>
    export {_ENV_PASSWORD}=<password>[/dim]

[bold]No credentials?[/bold]

  Get your credentials at [link=https://{_SIGNUP}]{_SIGNUP}[/link].

  Lost them? Get new ones at [link=https://{_REGEN}]{_REGEN}[/link].
"""


def login(credentials=None, credentials_file=None, endpoint="https://api.causalchamber.ai/v0", verbose=True):
    """Log in to the Remote Lab, returning a lab.Lab object to interact with it.

    The credentials are taken, in order of precedence, from the
    credentials argument, the credentials_file argument, or the
    environment variables CAUSALCHAMBER_USER and
    CAUSALCHAMBER_PASSWORD.

    If no credentials are found, an exception is raised explaining
    how to provide them. In interactive sessions (e.g., Jupyter or a
    terminal) the explanation is also printed in a readable format.

    Parameters
    ----------
    credentials : tuple of string or None, optional
        A tuple (<user>, <password>) with the user and password for
        the API.
    credentials_file : str or None, optional
        Path to the configuration file containing API
        credentials. The file should contain the following lines:
        ```
        [api_keys]
        user = <YOUR USERNAME>
        password = <YOUR PASSWORD>
        ```
    endpoint : str, optional
        Base URL for the API endpoint. Default is "https://api.causalchamber.ai/v0".
    verbose : bool, optional
        If True (default), this will print your user info (including
        your credits), your active real-time sessions and (up to 10
        of) your active experiments. If False, nothing is printed.

    Returns
    -------
    Lab
        The lab.Lab object to interact with the Remote Lab.

    Raises
    ------
    UserError
        If no credentials are provided, only one of the environment
        variables is set, or the credentials are incorrect.
    LabError
        If no connection to the API can be established or an
        internal error ocurred on our side.

    Examples
    --------
    >>> _ = os.environ.pop('CAUSALCHAMBER_USER', None)
    >>> _ = os.environ.pop('CAUSALCHAMBER_PASSWORD', None)
    >>> login()
    Traceback (most recent call last):
        ...
    causalchamber.lab.exceptions.UserError: (code 0) No credentials found. ...

    Setting only one of the environment variables raises an error.

    >>> os.environ['CAUSALCHAMBER_USER'] = 'username'
    >>> login()
    Traceback (most recent call last):
        ...
    causalchamber.lab.exceptions.UserError: (code 0) The environment variable CAUSALCHAMBER_USER is set but CAUSALCHAMBER_PASSWORD is not. ...

    With both set, the credentials are passed on to lab.Lab, which
    here fails to connect to a non-existing endpoint.

    >>> os.environ['CAUSALCHAMBER_PASSWORD'] = 'password'
    >>> login(endpoint='http://localhost:9999')
    Traceback (most recent call last):
        ...
    causalchamber.lab.exceptions.LabError: (code 1) Could not connect to the API at http://localhost:9999. ...
    >>> _ = os.environ.pop('CAUSALCHAMBER_USER', None)
    >>> _ = os.environ.pop('CAUSALCHAMBER_PASSWORD', None)
    """
    # If no credentials are passed as arguments, look in the environment variables
    if credentials is None and credentials_file is None:
        credentials = _credentials_from_env()
    # If none were found, explain how to provide them
    if credentials is None and credentials_file is None:
        if _is_interactive():
            _print_login_help()
            raise UserError(0, "No credentials found. See the instructions above.")
        else:
            from rich.text import Text
            raise UserError(0, "No credentials found. " + Text.from_markup(_LOGIN_HELP).plain)
    return Lab(credentials_file=credentials_file,
               endpoint=endpoint,
               verbose=verbose,
               credentials=credentials)


def _credentials_from_env():
    """Return the credentials (user, password) from the environment
    variables, or None if neither is set. Empty variables count as not
    set.

    Raises
    ------
    UserError
        If only one of the two environment variables is set.

    """
    user = os.environ.get(_ENV_USER) or None
    password = os.environ.get(_ENV_PASSWORD) or None
    if user is None and password is None:
        return None
    elif user is None or password is None:
        is_set, not_set = (_ENV_USER, _ENV_PASSWORD) if password is None else (_ENV_PASSWORD, _ENV_USER)
        raise UserError(0, f"The environment variable {is_set} is set but {not_set} is not. Set both, or pass your credentials as arguments to login.")
    else:
        return (user, password)


def _print_login_help():
    """Print the instructions to provide the credentials, formatted with rich."""
    from rich.console import Console
    note = f"\n{_LOGIN_HELP}"
    # Indent every (non-empty) line by two spaces
    note = "\n".join("  " + line if line else line for line in note.splitlines())
    console = Console(highlight=False)
    console.print("\n" + note + "\n\n\n")


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
            If True (default), this will print your user info
            (including your credits), your active real-time sessions
            and (up to 10 of) your active experiments. If False,
            nothing is printed.
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

        # Get the user's account (which also checks the credentials)
        # and optionally print the dashboard
        account = self.get_account()
        if verbose:
            print_dashboard(account)

    def get_account(self):
        """
        Retrieve the details of your account, including your credits,
        the chambers you can use, and your active real-time sessions
        and experiments.

        Returns
        -------
        dict
            Dictionary with the account details, including the
            user_id, name, email, institution, wallet (with your
            credits), chambers, sessions (active real-time sessions)
            and experiments (active experiments).

        Raises
        ------
        UserError
            If the credentials are incorrect.
        LabError
            If no connection to the API can be established or an
            internal error ocurred on our side.
        """
        response = self._API.make_request('GET', 'account')
        return response.json()['account']

    def dashboard(self):
        """
        Print the dashboard: your account and credits, the chambers
        you can use and when they are available, and your active
        real-time sessions and experiments.

        Raises
        ------
        UserError
            If the credentials are incorrect.
        LabError
            If no connection to the API can be established or an
            internal error ocurred on our side.
        """
        print_dashboard(self.get_account())

    def get_queue(self, chamber_id, verbose=True, print_max=10):
        """Retrieve the experiments that are waiting in the queue of the
        given chamber, including the experiment it is currently
        executing (if any).

        Parameters
        ----------
        chamber_id : str
            The unique identifier of the chamber.
        verbose : bool, optional
            If True (default), this will print a table with the
            experiments in the queue, their position and the user to
            whom they belong.
        print_max : int or None, optional
            Maximum number of queued experiments to print (if
            verbose=True). If None, all queued experiments are
            printed. Default is 10.

        Returns
        -------
        list of dict
            List of dictionaries containing the details of each
            experiment, including status, chamber_id, config, user,
            submission time, and other metadata, sorted by queue
            position. The experiment currently being executed (if any)
            has position 0.

        Raises
        ------
        TypeError
            If verbose=True and print_max is not an integer or None.
        ValueError
            If verbose=True and print_max is not larger than zero.
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
        sorted_by_position = sorted(experiments, key=lambda x: x['position'])
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
    
    def get_experiments(self, verbose=True, print_max=10):
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
            user are printed. Default is 10.

        Raises
        ------
        TypeError
            If verbose=True and print_max is not an integer or None.
        ValueError
            If verbose=True and print_max is not larger than zero.
        
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
        ExperimentDataset
            The downloaded dataset, which gives access to the
            experimental observations (ExperimentDataset.dataframe)
            and images, if any (ExperimentDataset.image_arrays or
            ExperimentDataset.image_iterator).

        Raises
        ------
        UserError
            If the experiment is not in 'DONE' status.
        FileNotFoundError
            If the root directory does not exist.
        requests.HTTPError
            If the data could not be downloaded, e.g., because the
            download link has expired.

        """
        experiment = self.get_experiment(experiment_id)
        current_status = experiment['status']
        # TODO: add a new branch for status CANCELED / FAILED / STOPPING
        # TODO: current branch should work for QUEUED and SUBMITTING
        # TODO: explicitly say: cannot download data because ...
        if current_status != 'DONE':
            raise UserError(code = 0,
                            message = f"Experiment '{experiment_id}' is not finished yet (current status = {current_status})",
                            scheduler_id = experiment.get('scheduler_id', None))
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

# Mid-tone colors with similar contrast (~4:1) on light and dark
# backgrounds, given as hex so terminals don't remap them
_GREEN = '#248f47'
_TEAL = '#158c8c'
_RED = '#e63f39'
_GREY = '#7d7d7d'

_STATUS_COLORS = {
    # Chamber status
    'READY': _GREEN,
    'LOADING': _TEAL,
    'EXECUTING': _TEAL,
    'ERROR': _RED,
    'OFFLINE': _RED,
    # Experiment status: the terminal's own palette colors, as in
    # earlier versions of the package (with termcolor)
    'QUEUED': 'yellow',
    'SUBMITTING': 'bright_yellow',
    'RUNNING': 'green',
    'STOPPING': 'magenta',
    'FAILED': 'bright_red',
    'CANCELED': '#969696',
    'DONE': 'bright_green',
    }

# Value shown for missing fields
_NA = "NA"


def _fmt_status(status):
    """
    Format a status string with the appropriate color.

    Parameters
    ----------
    status : str
        Status string to format (e.g., 'READY', 'RUNNING', 'DONE').

    Returns
    -------
    rich.text.Text
        The status, styled with its color (if it has one).

    Examples
    --------
    >>> _fmt_status('DONE').plain, _fmt_status('DONE').style
    ('DONE', 'bright_green')
    >>> _fmt_status('UNKNOWN').plain, _fmt_status('UNKNOWN').style
    ('UNKNOWN', '')
    >>> _fmt_status(None).plain
    'NA'
    """
    if status is None:
        return Text(_NA)
    return Text(str(status), style=_STATUS_COLORS.get(status, ''))


def _fmt_progress(experiment):
    """
    Return the percentage of instructions executed by an experiment, or
    'NA' if it is not available.

    Examples
    --------
    >>> _fmt_progress({'total_instructions': 6002, 'current_instruction': 5429})
    '90.45 %'
    >>> _fmt_progress({'total_instructions': 100, 'current_instruction': None})
    'NA'
    >>> _fmt_progress({})
    'NA'
    """
    try:
        current = float(experiment['current_instruction'])
        return f"{current / experiment['total_instructions'] * 100:.4g} %"
    except Exception:
        return _NA


def _cell(value):
    """Return a table cell for the given value, as plain text (i.e.,
    not parsed as rich markup), or 'NA' if the value is None."""
    return Text(_NA if value is None else str(value))


def _truncate(text, max_length=22):
    """
    Return the given text, trimmed at the end with '...' if it is
    longer than max_length characters, so that the result is at most
    max_length characters long. None is returned unchanged.

    Examples
    --------
    >>> _truncate('user123')
    'user123'
    >>> _truncate('a.very.long.username@example.com')
    'a.very.long.usernam...'
    >>> len(_truncate('a.very.long.username@example.com'))
    22
    >>> _truncate(None) is None
    True
    """
    if text is None or len(text) <= max_length:
        return text
    return text[:max_length - 3] + '...'


class _Table():
    """
    A rich renderable for tables in the style of this package: the
    column headers, a horizontal rule, the rows and a closing
    horizontal rule. The rules span the whole width of the table; there
    are two spaces before the first and after the last column, and
    three between columns. Cells never wrap.

    Besides rows, the table can contain labels: lines that span the
    whole table (e.g., '--- showing 10 / 20 experiments ---'), shown in
    grey and indented like the rows.
    """

    def __init__(self, headers, right_justified=()):
        """
        Parameters
        ----------
        headers : list of str
            The column headers.
        right_justified : collection of int, optional
            Indices of the columns that are right-justified. Default is
            none, i.e., all columns are left-justified.
        """
        self._headers = [Text(h) for h in headers]
        self._right_justified = set(right_justified)
        self._lines = []  # each entry is a list of cells (a row) or a Text (a label)

    def add_row(self, *cells):
        """Add a row; cells which are not rich Text are converted to
        plain text (i.e., not parsed as rich markup)."""
        self._lines.append([cell if isinstance(cell, Text) else _cell(cell) for cell in cells])

    def add_label(self, text):
        """Add a label, i.e., a grey line spanning the table. An empty
        string adds a blank line."""
        self._lines.append(Text(f"  {text}" if text else "", style=_GREY))

    def _widths(self):
        rows = [line for line in self._lines if isinstance(line, list)]
        return [max(cell.cell_len for cell in [header] + [row[i] for row in rows])
                for i, header in enumerate(self._headers)]

    def _format_row(self, cells, widths):
        line = Text("  ")
        for i, (cell, width) in enumerate(zip(cells, widths)):
            padding = " " * (width - cell.cell_len)
            line.append("   " if i > 0 else "")
            line.append_text(Text(padding) + cell if i in self._right_justified else cell + Text(padding))
        line.append("  ")
        return line

    def __rich_console__(self, console, options):
        widths = self._widths()
        rule = Text("─" * (sum(widths) + 3 * len(widths) + 1))
        yield self._format_row(self._headers, widths)
        yield rule
        for line in self._lines:
            yield self._format_row(line, widths) if isinstance(line, list) else line
        yield rule

    def __rich_measure__(self, console, options):
        widths = self._widths()
        width = max([sum(widths) + 3 * len(widths) + 1] +
                    [line.cell_len for line in self._lines if isinstance(line, Text)])
        return Measurement(width, width)


def _datetime_note():
    """Return the note, shown below tables, explaining that dates and
    times are given in the local timezone of the machine."""
    return Text(f" Date/time in your machine's local timezone — current time = {_fmt_timestamp(time.time())}")


def _print(*renderables):
    """
    Print the given rich renderables (e.g., strings, tables) one after
    the other.

    They are printed in a single call, so that Jupyter shows them in a
    single output block. Lines are never wrapped or cropped to fit the
    width of the console: if they are wider, they overflow as with
    print().
    """
    group = Group(*renderables)
    console = Console(highlight=False)
    width = Measurement.get(console, console.options.update(max_width=10_000), group).maximum
    if width > console.width:
        console = Console(highlight=False, width=width)
    console.print(group)


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
    

def _chamber_table(chambers):
    """
    Return a renderable with a table of chamber information.

    Parameters
    ----------
    chambers : list of dict
        List of dictionaries containing chamber information. Each dictionary
        should have keys: 'status', 'chamber_id', 'chamber_model', 'mode',
        and 'valid_configs'.

    Returns
    -------
    rich renderable
    """
    table = _Table(["Status", "Chamber ID", "Model", "Mode", "Hardware Configurations"])
    for chamber in chambers:
        valid_configs = chamber.get('valid_configs', None)
        if isinstance(valid_configs, list):
            valid_configs = ', '.join(f"'{config}'" for config in valid_configs)
        table.add_row(_fmt_status(chamber.get('status')),
                      _cell(chamber.get('chamber_id')),
                      _cell(chamber.get('chamber_model')),
                      _cell(chamber.get('mode')),
                      _cell(valid_configs))
    return table


def _print_chamber_table(chambers):
    """
    Print a formatted table of chamber information.

    Parameters
    ----------
    chambers : list of dict
        List of dictionaries containing chamber information (see _chamber_table).

    Examples
    --------
    >>> chambers = [
    ...     {'status': 'READY', 'chamber_id': 'lt-demo-x81a', 'chamber_model': 'Light Tunnel Mk2',
    ...      'mode': 'queue', 'valid_configs': ['standard', 'camera']},
    ...     {'status': 'OFFLINE', 'chamber_id': 'wt-demo-c2q4', 'chamber_model': 'Wind Tunnel Mk2',
    ...      'mode': None, 'valid_configs': ['standard']}
    ... ]
    >>> _print_chamber_table(chambers) # doctest: +NORMALIZE_WHITESPACE
    <BLANKLINE>
      Status    Chamber ID     Model              Mode    Hardware Configurations
    ───────────────────────────────────────────────────────────────────────────────
      READY     lt-demo-x81a   Light Tunnel Mk2   queue   'standard', 'camera'
      OFFLINE   wt-demo-c2q4   Wind Tunnel Mk2    NA      'standard'
    ───────────────────────────────────────────────────────────────────────────────
    """
    _print("", _chamber_table(chambers))


def _check_print_max(print_max):
    """
    Check that print_max is None or an integer larger than zero.

    Raises
    ------
    TypeError
        If print_max is not an integer or None.
    ValueError
        If print_max is less than or equal to zero.
    """
    if print_max is not None and (isinstance(print_max, bool) or not isinstance(print_max, numbers.Integral)):
        raise TypeError(f"print_max must be an integer or None, not {type(print_max).__name__}")
    if print_max is not None and print_max <= 0:
        raise ValueError("print_max must be None or an integer larger than zero")


def _experiment_table(experiments, print_max=None):
    """
    Return a renderable with a table of experiment information,
    followed by a note on the timezone of the dates.

    Parameters
    ----------
    experiments : list of dict
        List of dictionaries containing experiment information. Each dictionary
        should have keys: 'status', 'tag', 'experiment_id', 'chamber_id',
        'config', and 'submitted_on', and optionally
        'total_instructions' and 'current_instruction' to show the
        progress.
    print_max : int or None, optional
        Maximum number of experiments to print. If None, all experiments
        are printed. Default is None.

    Returns
    -------
    rich renderable

    Raises
    ------
    TypeError
        If print_max is not an integer or None.
    ValueError
        If print_max is less than or equal to zero.
    """
    _check_print_max(print_max)
    n = len(experiments) if print_max is None else min(print_max, len(experiments))
    table = _Table(_EXPERIMENT_HEADERS)
    for experiment in experiments[0:n]:
        _add_experiment_row(table, experiment)
    if n < len(experiments):
        table.add_label("")
        table.add_label(f"--- showing {n} / {len(experiments)} experiments ---")
    return Group(table, _datetime_note())


def _add_experiment_row(table, experiment):
    """Add a row with the given experiment to a table with the
    columns in _EXPERIMENT_HEADERS."""
    submitted_on = experiment.get('submitted_on', None)
    table.add_row(_fmt_status(experiment.get('status')),
                  _fmt_progress(experiment),
                  experiment.get('tag'),
                  experiment.get('experiment_id'),
                  experiment.get('chamber_id'),
                  experiment.get('config'),
                  _NA if submitted_on is None else _fmt_timestamp(submitted_on))


_EXPERIMENT_HEADERS = ["Status", "Progress", "Tag", "Experiment ID", "Chamber ID", "Config", "Submitted On"]


def _print_experiment_table(experiments, print_max=None):
    """
    Print a formatted table of experiment information.

    Parameters
    ----------
    experiments : list of dict
        List of dictionaries containing experiment information (see
        _experiment_table).
    print_max : int or None, optional
        Maximum number of experiments to print. If None, all experiments
        are printed. Default is None.

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
    >>> _print_experiment_table(experiments, print_max=10) # doctest: +NORMALIZE_WHITESPACE
    <BLANKLINE>
      Status   Progress   Tag     Experiment ID   Chamber ID   Config     Submitted On
    ──────────────────────────────────────────────────────────────────────────────────────────────────────
      DONE     NA         test1   exp_01          ch_01        config_A   Sat, Feb 14, 2009 00:31:30 CET
    ──────────────────────────────────────────────────────────────────────────────────────────────────────
     Date/time in your machine's local timezone — current time = ...
    <BLANKLINE>

    The progress is shown if the experiment has the necessary fields,
    and a label is shown if not all experiments are printed.

    >>> experiments.append(
    ...     {'status': 'RUNNING', 'tag': 'test2', 'experiment_id': 'exp_02', 'total_instructions': 6002, 'current_instruction': 5429,
    ...      'chamber_id': 'ch_01', 'config': 'config_A', 'submitted_on': 1234567890}
    ... )
    >>> _print_experiment_table(experiments[::-1], print_max=1) # doctest: +NORMALIZE_WHITESPACE
    <BLANKLINE>
      Status    Progress   Tag     Experiment ID   Chamber ID   Config     Submitted On
    ───────────────────────────────────────────────────────────────────────────────────────────────────────
      RUNNING   90.45 %    test2   exp_02          ch_01        config_A   Sat, Feb 14, 2009 00:31:30 CET
    <BLANKLINE>
      --- showing 1 / 2 experiments ---
    ───────────────────────────────────────────────────────────────────────────────────────────────────────
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
    _print("", _experiment_table(experiments, print_max), "")


def _queue_table(experiments, chamber_id, print_max=None):
    """
    Return a renderable with the queue of a chamber: a title, a table
    with the experiment currently being executed (if any) followed by
    the queued experiments, and notes on how many experiments are
    shown and the timezone of the dates.

    Parameters
    ----------
    experiments : list of dict
        List of dictionaries containing experiment information. Each dictionary
        should have keys: 'status', 'tag', 'experiment_id', 'user_id',
        'submitted_on' and 'position', where position 0 denotes the
        experiment currently being executed. Running experiments can
        also have the keys 'current_instruction' and
        'total_instructions' to display their progress.
    chamber_id : str
        The unique identifier of the chamber, shown in the title.
    print_max : int or None, optional
        Maximum number of queued experiments to print; the experiment
        currently being executed is always printed. If None, all
        experiments are printed. Default is None.

    Returns
    -------
    rich renderable

    Raises
    ------
    TypeError
        If print_max is not an integer or None.
    ValueError
        If print_max is less than or equal to zero.
    """
    _check_print_max(print_max)
    title = Text(f"Active and queued experiments for chamber '{chamber_id}'. Position 1 is the next to run.")
    # Separate the active experiment (position=0) from the queue (position>0)
    active = next((e for e in experiments if e.get('position') == 0), None)
    queued = [e for e in experiments if e.get('position') != 0]
    n = len(queued) if print_max is None else min(print_max, len(queued))

    def add_row(experiment):
        status = experiment.get('status')
        if status == 'SUBMITTING':
            position = '>>'
        elif status in ('RUNNING', 'STOPPING'):
            position = _fmt_progress(experiment)
        else:
            position = experiment.get('position')
        submitted_on = experiment.get('submitted_on', None)
        table.add_row(position,
                      _fmt_status(status),
                      experiment.get('tag'),
                      experiment.get('experiment_id'),
                      _truncate(experiment.get('user_id')),
                      _NA if submitted_on is None else _fmt_timestamp(submitted_on))

    table = _Table(["", "Status", "Tag", "Experiment ID", "Submitted By", "Submitted On"], right_justified=[0])
    if active is not None:
        table.add_label("--- Active experiment ---")
        add_row(active)
        table.add_label("")
    if n > 0:
        table.add_label("--- Queued experiments ---")
    for experiment in queued[0:n]:
        add_row(experiment)
    if n < len(queued):
        table.add_label("")
        table.add_label(f"--- showing {n} / {len(queued)} queued experiments ---")
    if n == 0:
        table.add_label("--- There are no experiments in the queue ---")
    return Group(title, "", table, _datetime_note())


def _print_queue_table(experiments, chamber_id, print_max=None):
    """
    Print a formatted table with the queue of a chamber.

    Parameters
    ----------
    experiments : list of dict
        List of dictionaries containing experiment information (see
        _queue_table).
    chamber_id : str
        The unique identifier of the chamber, shown in the title.
    print_max : int or None, optional
        Maximum number of queued experiments to print; the experiment
        currently being executed is always printed. If None, all
        experiments are printed. Default is None.

    Raises
    ------
    TypeError
        If print_max is not an integer or None.
    ValueError
        If print_max is less than or equal to zero.
    
    Examples
    --------
    >>> _print_queue_table([], 'ch-abcd-xyzw', print_max=10) # doctest: +NORMALIZE_WHITESPACE
    <BLANKLINE>
    Active and queued experiments for chamber 'ch-abcd-xyzw'. Position 1 is the next to run.
    <BLANKLINE>
         Status   Tag   Experiment ID   Submitted By   Submitted On
    ─────────────────────────────────────────────────────────────────
      --- There are no experiments in the queue ---
    ─────────────────────────────────────────────────────────────────
     Date/time in your machine's local timezone — current time = ...
    <BLANKLINE>

    >>> experiments = [
    ...     {'status': 'QUEUED', 'tag': 'test1', 'experiment_id': 'exp_01',
    ...      'chamber_id': 'ch-abcd-xyzw', 'config': 'config_A', 'submitted_on': 1234567890, 'user_id': 'test@test', 'position': 1}
    ... ]
    >>> _print_queue_table(experiments, 'ch-abcd-xyzw', print_max=10) # doctest: +NORMALIZE_WHITESPACE
    <BLANKLINE>
    Active and queued experiments for chamber 'ch-abcd-xyzw'. Position 1 is the next to run.
    <BLANKLINE>
          Status   Tag     Experiment ID   Submitted By   Submitted On
    ──────────────────────────────────────────────────────────────────────────────────────
      --- Queued experiments ---
      1   QUEUED   test1   exp_01          test@test      Sat, Feb 14, 2009 00:31:30 CET
    ──────────────────────────────────────────────────────────────────────────────────────
     Date/time in your machine's local timezone — current time = ...
    <BLANKLINE>

    >>> experiments_with_active = [
    ...     {'status': 'RUNNING', 'tag': 'active1', 'experiment_id': 'exp_00',
    ...      'chamber_id': 'ch-abcd-xyzw', 'config': 'config_A', 'submitted_on': 1234567890,
    ...      'user_id': 'test@test', 'position': 0, 'current_instruction': 50, 'total_instructions': 200},
    ...     {'status': 'QUEUED', 'tag': 'test1', 'experiment_id': 'exp_01',
    ...      'chamber_id': 'ch-abcd-xyzw', 'config': 'config_A', 'submitted_on': 1234567890,
    ...      'user_id': 'test@test', 'position': 1}
    ... ]
    >>> _print_queue_table(experiments_with_active, 'ch-abcd-xyzw', print_max=10) # doctest: +NORMALIZE_WHITESPACE
    <BLANKLINE>
    Active and queued experiments for chamber 'ch-abcd-xyzw'. Position 1 is the next to run.
    <BLANKLINE>
             Status    Tag       Experiment ID   Submitted By   Submitted On
    ────────────────────────────────────────────────────────────────────────────────────────────
      --- Active experiment ---
      25 %   RUNNING   active1   exp_00          test@test      Sat, Feb 14, 2009 00:31:30 CET
    <BLANKLINE>
      --- Queued experiments ---
         1   QUEUED    test1     exp_01          test@test      Sat, Feb 14, 2009 00:31:30 CET
    ────────────────────────────────────────────────────────────────────────────────────────────
     Date/time in your machine's local timezone — current time = ...
    <BLANKLINE>

    >>> many_experiments = [
    ...     {'status': 'QUEUED', 'tag': 'test1', 'experiment_id': 'exp_01',
    ...      'chamber_id': 'ch-abcd-xyzw', 'config': 'config_A', 'submitted_on': 1234567890,
    ...      'user_id': 'test@test', 'position': 1},
    ...     {'status': 'QUEUED', 'tag': 'test2', 'experiment_id': 'exp_02',
    ...      'chamber_id': 'ch-abcd-xyzw', 'config': 'config_A', 'submitted_on': 1234567890,
    ...      'user_id': 'test@test', 'position': 2},
    ...     {'status': 'QUEUED', 'tag': 'test3', 'experiment_id': 'exp_03',
    ...      'chamber_id': 'ch-abcd-xyzw', 'config': 'config_A', 'submitted_on': 1234567890,
    ...      'user_id': 'test@test', 'position': 3}
    ... ]
    >>> _print_queue_table(many_experiments, 'ch-abcd-xyzw', print_max=2) # doctest: +NORMALIZE_WHITESPACE
    <BLANKLINE>
    Active and queued experiments for chamber 'ch-abcd-xyzw'. Position 1 is the next to run.
    <BLANKLINE>
          Status   Tag     Experiment ID   Submitted By   Submitted On
    ──────────────────────────────────────────────────────────────────────────────────────
      --- Queued experiments ---
      1   QUEUED   test1   exp_01          test@test      Sat, Feb 14, 2009 00:31:30 CET
      2   QUEUED   test2   exp_02          test@test      Sat, Feb 14, 2009 00:31:30 CET
    <BLANKLINE>
      --- showing 2 / 3 queued experiments ---
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
    _print("", _queue_table(experiments, chamber_id, print_max), "")


# ----------------------------------------------------------------------
# Doctests

if __name__ == "__main__":
    import doctest
    doctest.testmod(
        extraglobs={},
        verbose=True,
        optionflags=doctest.ELLIPSIS,
    )
