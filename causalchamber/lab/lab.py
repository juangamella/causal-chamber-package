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
import math
import numbers
import warnings

# Third-party packages
import numpy as np
import pandas as pd
import yaml
from PIL import Image

# Imports from this package
from causalchamber.lab.utils import download_and_extract
from causalchamber.lab.chamber import Batch, Chamber
from causalchamber.lab.api import API
from causalchamber.lab.exceptions import LabError, UserError
from causalchamber import _is_interactive, _PROMPT, _CODE_STYLE
from causalchamber.lab.rendering import (print_dashboard, print_chamber, print_experiments,
                                         print_topup, print_transactions, run_monitor, _fmt_seconds)

# Minimum number of seconds between refreshes of Lab.monitor
_MIN_REFRESH_RATE = 5

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

# Summary of the instructions above, as the message of the exception
_NO_CREDENTIALS = (
    "No credentials found. Pass the path to your credentials file with "
    "lab.login(credentials_file=\"path/to/credentials_file\"), or set the environment "
    f"variables {_ENV_USER} and {_ENV_PASSWORD} before starting Python or Jupyter. "
    f"No credentials? Get them at https://{_SIGNUP}."
)


def login(credentials=None, credentials_file=None, endpoint="https://api.causalchamber.ai/v1", verbose=True):
    """Log in to the Remote Lab, returning a lab.Lab object to interact with it.

    The credentials are taken, in order of precedence, from the
    credentials argument, the credentials_file argument, or the
    environment variables CAUSALCHAMBER_USER and
    CAUSALCHAMBER_PASSWORD.

    If no credentials are found, an exception is raised summarizing
    how to provide them. In interactive sessions (e.g., Jupyter or a
    terminal) detailed instructions are also printed.

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
        Base URL for the API endpoint. Default is "https://api.causalchamber.ai/v1".
    verbose : bool, optional
        If True (default), this will print your user info (including
        your credits), your active interactive sessions and (up to 10
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
    causalchamber.lab.exceptions.UserError: (code 0) No credentials found. Pass the path to your credentials file with lab.login(credentials_file="path/to/credentials_file"), or set the environment variables CAUSALCHAMBER_USER and CAUSALCHAMBER_PASSWORD before starting Python or Jupyter. No credentials? Get them at https://forms.causalchamber.ai/signup.
    ...

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
        raise UserError(0, _NO_CREDENTIALS)
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
      - monitor your account, chambers, sessions and experiments
      - top up your credits and see their transactions
      - check the details of a chamber, including its queue, and
        change its mode (if you have the permission)
      - create, submit and cancel experiments in a chamber's queue
      - download the data from completed experiments
      - start and stop interactive sessions with a chamber
    """

    def __init__(self, credentials_file=None, endpoint="https://api.causalchamber.ai/v1", verbose=True, credentials=None):
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
            Base URL for the API endpoint. Default is "https://api.causalchamber.ai/v1".
        verbose : bool, optional
            If True (default), this will print your user info
            (including your credits), your active interactive sessions
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
        if verbose:
            self.dashboard()
        else:
            self.get_account()

    def dashboard(self):
        """
        Print the dashboard: your account and credits, the chambers
        you can use and when they are available, and your active
        interactive sessions and experiments. To show it live, see
        Lab.monitor.

        Returns
        -------
        dict
            The account details shown in the dashboard (see
            Lab.get_account).

        Raises
        ------
        UserError
            If the credentials are incorrect.
        LabError
            If no connection to the API can be established or an
            internal error ocurred on our side.
        """
        account = self.get_account()
        print_dashboard(account)
        return account

    def get_account(self):
        """
        Retrieve the details of your account, including your credits,
        the chambers you can use, and your active interactive sessions
        and experiments.

        Returns
        -------
        dict
            Dictionary with the account details, including the
            user_id, name, email, institution, wallet (with your
            credits), chambers, sessions (active interactive sessions)
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
        account = response.json()['account']
        # Remember the user's wallet, to top it up (see Lab.topup)
        self._wallet_id = account['wallet']['wallet_id']
        return account

    def topup(self, verbose=True):
        """
        Show the ways to top up your credits, e.g., payment links or
        instructions to pay by invoice.

        Parameters
        ----------
        verbose : bool, optional
            If True (default), the ways to top up your credits are
            printed. If False, nothing is printed.

        Returns
        -------
        dict
            The ways to top up your credits, by name (e.g.,
            'invoice'): payment links, or instructions.

        Raises
        ------
        UserError
            If the credentials are incorrect, or the wallet of your
            account changed since you logged in (code 404).
        LabError
            If no connection to the API can be established or an
            internal error ocurred on our side.
        """
        response = self._API.make_request('POST', f'wallet/{self._wallet_id}/topup',
                                          not_found="The wallet of your account changed since you logged in. Please log in again with lab.login().")
        payment_links = response.json()['payment_links']
        if verbose:
            print_topup(payment_links)
        return payment_links

    def get_transactions(self, verbose=True, fetch_max=10):
        """
        Retrieve the latest transactions of your wallet (every change
        of its credits, e.g., charges, refunds and top-ups), newest
        first.

        Parameters
        ----------
        verbose : bool, optional
            If True (default), the transactions are printed. If False,
            nothing is printed.
        fetch_max : int, optional
            Maximum number of transactions to retrieve (the latest
            ones). Default is 10.

        Returns
        -------
        list of dict
            The transactions, newest first.

        Raises
        ------
        TypeError
            If fetch_max is not an integer.
        ValueError
            If fetch_max is not larger than zero.
        UserError
            If the credentials are incorrect, or fetch_max is larger
            than allowed by the API (code 400).
        LabError
            If no connection to the API can be established or an
            internal error ocurred on our side.
        """
        _check_positive_int(fetch_max, 'fetch_max')
        response = self._API.make_request('GET', 'transactions', query={'limit': fetch_max})
        transactions = response.json()['transactions']
        if verbose:
            print_transactions(transactions, self._API.user_id, fetch_max)
        return transactions

    def monitor(self, refresh_rate=5):
        """
        Show the dashboard live: your account and credits, the
        chambers you can use and when they are available, and your
        active interactive sessions and experiments, refreshed every
        refresh_rate seconds. Stop it with Ctrl+C.

        Parameters
        ----------
        refresh_rate : int or float, optional
            Seconds between refreshes, at least 5. Default is 5.

        Raises
        ------
        TypeError
            If refresh_rate is not a number.
        ValueError
            If refresh_rate is smaller than 5 or not finite.
        UserError
            If the credentials are incorrect.
        LabError
            If no connection to the API can be established or an
            internal error ocurred on our side.
        """
        _check_refresh_rate(refresh_rate)
        run_monitor(self.get_account, refresh_rate)

    def new_session(self, chamber_id, config, duration, verbose=True):
        """
        Start an interactive session with a chamber, returning a
        lab.Session object to control it in real time.

        The chamber resets and loads the given configuration. The
        whole duration of the session is charged when it starts (1
        credit per second, including the time it takes the chamber
        to reset), and the unused time is refunded if you stop it
        before it expires (see Session.stop). The session can also be
        used as a context manager, which stops it on exit, e.g.,

            with rlab.new_session('lt-demo-x81a', 'standard', duration=600) as session:
                session.set('red', 255)
                data = session.measure(n=10)

        Parameters
        ----------
        chamber_id : str
            The unique identifier of the chamber.
        config : str
            The configuration the chamber should load.
        duration : int
            The maximum duration of the session, in seconds.
        verbose : bool, optional
            If True (default), progress messages and the details of
            the session are printed. If False, nothing is printed.

        Returns
        -------
        Session
            The lab.Session object to control the chamber.

        Raises
        ------
        UserError
            If the credentials are incorrect, the chamber does not
            exist or is not in interactive mode, the configuration
            or duration are invalid, the chamber is in use by another
            session, or you do not have enough credits.
        LabError
            If no connection to the API can be established or an error
            on our side prevents starting the session.
        """
        return Session(self, chamber_id, config, duration, verbose=verbose)

    def stop_session(self, session_id, verbose=True):
        """
        Stop one of your active interactive sessions. Its
        instructions are refused from then on, and the credits for
        its unused time (1 credit per whole second) are refunded.

        Your active sessions are listed in the dashboard (see
        Lab.dashboard or Lab.monitor).

        Parameters
        ----------
        session_id : str
            The unique identifier of the session.
        verbose : bool, optional
            If True (default), this will print a confirmation with the
            refunded credits. If False, nothing is printed.

        Returns
        -------
        dict
            The stopped session, including its refund (in credits) and
            its unused_seconds.

        Raises
        ------
        TypeError
            If session_id is not a string.
        UserError
            If the credentials are incorrect, the session does not
            exist or does not belong to you (code 404), or it is no
            longer active, i.e., it was already stopped, its time is
            up, or it was replaced by a newer session (code 409).
        LabError
            If no connection to the API can be established or an
            internal error ocurred on our side.
        """
        _check_id(session_id, 'session_id')
        response = self._API.make_request('POST', f'sessions/{session_id}/stop',
                                          not_found=f"Session '{session_id}' does not exist or does not belong to you.")
        session = response.json()['session']
        if verbose:
            print(f"Stopped session {session_id}; {session.get('refund', 0):,} credits were refunded for its unused time.")
        return session

    def get_chamber(self, chamber_id, verbose=True, print_max=10):
        """
        Retrieve the details of a chamber: whether it is in use and
        when it is available, its configurations (with links to
        their documentation), and its queue (in queue mode) or active
        session (in interactive mode).

        Parameters
        ----------
        chamber_id : str
            The unique identifier of the chamber.
        verbose : bool, optional
            If True (default), the details are printed. If False,
            nothing is printed.
        print_max : int or None, optional
            Maximum number of queued experiments to print (if
            verbose=True). If None, all are printed. Default is 10.

        Returns
        -------
        dict
            The chamber, with its chamber_id, chamber_model, mode,
            chamber_state, available_on, configs, queue (in queue
            mode; None otherwise) and session (None if it has no
            active session). The queue starts with the experiment in
            flight, if any (position 0), followed by the queued ones
            in order.

        Raises
        ------
        TypeError
            If chamber_id is not a string, or print_max is not an
            integer or None.
        ValueError
            If print_max is not larger than zero.
        UserError
            If the credentials are incorrect, or the chamber does not
            exist or you do not have access to it (code 404).
        LabError
            If no connection to the API can be established or an
            internal error ocurred on our side.
        """
        _check_id(chamber_id, 'chamber_id')
        _check_positive_int(print_max, 'print_max', allow_none=True)
        response = self._API.make_request('GET', f'chambers/{chamber_id}',
                                          not_found=f"Chamber '{chamber_id}' does not exist or you do not have access to it.")
        chamber = response.json()['chamber']
        if verbose:
            print_chamber(chamber, self._API.user_id, print_max=print_max)
        return chamber

    def get_queue(self, chamber_id, verbose=True, print_max=10):
        """
        Retrieve the details of a chamber, including its queue. Same
        as Lab.get_chamber, see its documentation.
        """
        return self.get_chamber(chamber_id, verbose=verbose, print_max=print_max)

    def change_chamber_mode(self, chamber_id, mode):
        """
        Change the mode of a chamber to 'interactive' (it runs
        interactive sessions) or 'queue' (it runs the experiments in
        its queue). Requires the permission to change the chamber's
        mode.

        The chamber can only leave interactive mode if it has no
        active session, and queue mode if it has no experiments
        queued or in flight. Changing to the chamber's current mode
        always succeeds.

        Parameters
        ----------
        chamber_id : str
            The unique identifier of the chamber.
        mode : str
            The new mode: 'interactive' or 'queue'.

        Returns
        -------
        dict
            The chamber after the change, with its chamber_id,
            chamber_model, mode, chamber_state and available_on.

        Raises
        ------
        TypeError
            If chamber_id or mode are not strings.
        ValueError
            If mode is not 'interactive' or 'queue'.
        UserError
            If the credentials are incorrect, you do not have the
            permission to change the chamber's mode (code 403), the
            chamber does not exist or you do not have access to it
            (code 404), or the chamber is still in use in its current
            mode (code 409).
        LabError
            If no connection to the API can be established or an
            internal error ocurred on our side, or the chamber is busy
            with another request (code 503; try again in a few
            seconds).
        """
        _check_id(chamber_id, 'chamber_id')
        _check_mode(mode)
        response = self._API.make_request('PUT', f'chambers/{chamber_id}/mode', {'mode': mode},
                                          not_found=f"Chamber '{chamber_id}' does not exist or you do not have access to it.")
        return response.json()['chamber']

    def get_experiment(self, experiment_id):
        """
        Retrieve the details of one of your experiments.

        Parameters
        ----------
        experiment_id : str
            The unique identifier of the experiment.

        Returns
        -------
        dict
            The experiment, including its status, chamber_id,
            chamber_config, submission time, progress and, once it is
            DONE, the download_url of its data.

        Raises
        ------
        TypeError
            If experiment_id is not a string.
        UserError
            If the credentials are incorrect, the experiment_id is
            invalid (code 400), or the experiment does not exist or
            does not belong to you (code 404).
        LabError
            If no connection to the API can be established or an
            internal error ocurred on our side.
        """
        _check_id(experiment_id, 'experiment_id')
        response = self._API.make_request('GET', f'experiments/{experiment_id}',
                                          not_found=f"Experiment '{experiment_id}' does not exist or does not belong to you.")
        return response.json()['experiment']

    def get_experiments(self, verbose=True, fetch_max=10):
        """
        Retrieve your latest experiments, on any chamber, newest first.

        Parameters
        ----------
        verbose : bool, optional
            If True (default), the experiments are printed, split in
            in flight, queued and finished. If False, nothing is
            printed.
        fetch_max : int, optional
            Maximum number of experiments to retrieve (the latest
            ones). Default is 10.

        Returns
        -------
        list of dict
            The experiments, newest first.

        Raises
        ------
        TypeError
            If fetch_max is not an integer.
        ValueError
            If fetch_max is not larger than zero.
        UserError
            If the credentials are incorrect, or fetch_max is larger
            than allowed by the API (code 400).
        LabError
            If no connection to the API can be established or an
            internal error ocurred on our side.
        """
        _check_positive_int(fetch_max, 'fetch_max')
        response = self._API.make_request('GET', 'experiments', query={'limit': fetch_max})
        experiments = response.json()['experiments']
        if verbose:
            print_experiments(experiments, self._API.user_id, fetch_max)
        return experiments

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
            The lab.Protocol object that can be used to add
            instructions, check the cost of the experiment and submit
            it.

        """
        return Protocol(chamber_id, config, self._API)

    def cancel_experiment(self, experiment_id):
        """
        Cancel one of your experiments. A queued experiment is
        canceled at once and its charge refunded in full. A running
        experiment is stopped by the chamber before its next
        instruction (its status is then STOPPING, and CANCELED once
        stopped), and the credits for its unused time are refunded.

        Parameters
        ----------
        experiment_id : str
            The unique identifier of the experiment to cancel.

        Returns
        -------
        dict
            The experiment, with its updated status.

        Raises
        ------
        TypeError
            If experiment_id is not a string.
        UserError
            If the credentials are incorrect, the experiment does not
            exist or does not belong to you (code 404), or it cannot
            be canceled, e.g., because it already finished (code 409).
        LabError
            If no connection to the API can be established or an
            internal error ocurred on our side.
        """
        _check_id(experiment_id, 'experiment_id')
        response = self._API.make_request('POST', f'experiments/{experiment_id}/cancel',
                                          not_found=f"Experiment '{experiment_id}' does not exist or does not belong to you.")
        return response.json()['experiment']

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
            If the experiment is not in 'DONE' status, or it does not
            exist or does not belong to you (code 404).
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
                            message = f"Experiment '{experiment_id}' is not finished yet (current status = {current_status})")
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
            for the given chamber & config, the user has reached the
            maximum number of experiments in the queue, or does not
            have enough credits.
        LabError
            If no connection to the API can be established or an error
            on our side prevents submitting the experiment.

        """
        # POST /experiments
        body = self._body()
        if tag is not None and not isinstance(tag, str):
            raise TypeError(f"tag must be str, not {type(tag).__name__}")
        elif tag is not None:
            body['tag'] = tag
        response = self._API.make_request('POST', 'experiments', body)
        # Return the experiment id
        return response.json()['experiment']['experiment_id']

    def cost(self, verbose=True):
        """Return the most the experiment can cost, in credits, without
        submitting it.

        When the experiment is submitted, its estimated runtime is
        charged (1 credit per second). If it finishes earlier, the
        difference is refunded; if it takes longer, nothing more is
        charged.

        Parameters
        ----------
        verbose : bool, optional
            If True (default), the cost and estimated runtime are
            printed. If False, nothing is printed.

        Returns
        -------
        int
            The most the experiment can cost, in credits.

        Raises
        ------
        UserError
            If the protocol contains invalid / incorrect instructions
            for the given chamber & config, or exceeds the limits of
            the chamber's queue.
        LabError
            If no connection to the API can be established or an
            internal error ocurred on our side.

        """
        response = self._API.make_request('POST', 'experiments/quote', self._body())
        quote = response.json()['quote']
        cost = quote['credits_max']
        if verbose:
            print(f"This experiment will cost at most {cost:,} credits (estimated runtime is "
                  f"{_fmt_seconds(quote['est_runtime_seconds'])}). If the experiment finishes "
                  "before the estimated runtime, we will refund the difference.")
        return cost

    def _body(self):
        """Return the body of the requests to submit or quote the protocol."""
        return {'chamber_id': self._chamber_id,
                'chamber_config': self._config,
                'instructions': self._instructions}


class Session(Chamber):
    """
    An interactive session with a chamber, to control it in real
    time. Returned by Lab.new_session; see the lab.Chamber class for
    the methods to send instructions to the chamber.

    It can be used as a context manager, which stops the session on
    exit (see Session.stop).
    """

    def __init__(self, lab, chamber_id, config, duration, verbose=True):
        """
        Start a new interactive session. Use Lab.new_session instead.

        Parameters
        ----------
        lab : lab.Lab
            The lab which started the session, whose API client the
            session uses.
        chamber_id : str
            The unique identifier of the chamber.
        config : str
            The configuration the chamber should load.
        duration : int
            The maximum duration of the session, in seconds.
        verbose : bool, optional
            If True (default), progress messages and the details of
            the session are printed. If False, nothing is printed.
        """
        # We purposefully overwrite the init method of
        # lab.chamber.Chamber, to reuse the API client of the lab
        self._lab = lab
        self._API = lab._API
        self._start_session(chamber_id, config, duration, verbose)

    def stop(self):
        """
        Stop the session. Its instructions are refused from then on,
        and the credits for its unused time (1 credit per whole
        second) are refunded. See Lab.stop_session.

        Returns
        -------
        dict
            The stopped session, including its refund (in credits) and
            its unused_seconds.

        Raises
        ------
        UserError
            If the session is no longer active, i.e., it was already
            stopped, its time is up, or it was replaced by a newer
            session (code 409).
        LabError
            If no connection to the API can be established or an
            internal error ocurred on our side.
        """
        return self._lab.stop_session(self.session_id, verbose=bool(self.verbose))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Stop the session, unless it is no longer active. If the
        block raised an exception, a failure to stop the session is
        only warned about, so that it does not hide the exception."""
        try:
            self.stop()
        except UserError as e:
            # Already stopped, expired or replaced: nothing to stop
            if e.code != 409:
                _raise_or_warn(e, exc_type, self.session_id)
        except LabError as e:
            _raise_or_warn(e, exc_type, self.session_id)
        # Do not suppress the exception raised in the block, if any
        return False



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

def _raise_or_warn(error, exc_type, session_id):
    """Raise the error from stopping a session on exiting its context,
    or only warn about it if the block raised an exception (exc_type
    is not None), so that it does not hide it."""
    if exc_type is None:
        raise error
    warnings.warn(f"Could not stop session '{session_id}': {error.message}")


def _check_id(value, name):
    """
    Check that an id (e.g., experiment_id) is a string.

    Examples
    --------
    >>> _check_id('f47ac10b', 'experiment_id')
    >>> _check_id(123, 'experiment_id')
    Traceback (most recent call last):
        ...
    TypeError: experiment_id must be a string, not int
    """
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string, not {type(value).__name__}")


def _check_mode(mode):
    """
    Check that a chamber mode is 'interactive' or 'queue'.

    Examples
    --------
    >>> _check_mode('queue')
    >>> _check_mode('real-time')
    Traceback (most recent call last):
        ...
    ValueError: mode must be 'interactive' or 'queue', not 'real-time'
    >>> _check_mode(None)
    Traceback (most recent call last):
        ...
    TypeError: mode must be a string, not NoneType
    """
    if not isinstance(mode, str):
        raise TypeError(f"mode must be a string, not {type(mode).__name__}")
    elif mode not in ('interactive', 'queue'):
        raise ValueError(f"mode must be 'interactive' or 'queue', not {mode!r}")


def _check_positive_int(value, name, allow_none=False):
    """
    Check that a value is an integer larger than zero (or None, if
    allow_none=True).

    Examples
    --------
    >>> _check_positive_int(10, 'fetch_max')
    >>> _check_positive_int(None, 'print_max', allow_none=True)
    >>> _check_positive_int(None, 'fetch_max')
    Traceback (most recent call last):
        ...
    TypeError: fetch_max must be an integer, not NoneType
    >>> _check_positive_int(True, 'fetch_max')
    Traceback (most recent call last):
        ...
    TypeError: fetch_max must be an integer, not bool
    >>> _check_positive_int(2.0, 'print_max', allow_none=True)
    Traceback (most recent call last):
        ...
    TypeError: print_max must be an integer or None, not float
    >>> _check_positive_int(0, 'fetch_max')
    Traceback (most recent call last):
        ...
    ValueError: fetch_max must be larger than zero, not 0
    """
    if value is None and allow_none:
        return
    if not isinstance(value, numbers.Integral) or isinstance(value, bool):
        expected = "an integer or None" if allow_none else "an integer"
        raise TypeError(f"{name} must be {expected}, not {type(value).__name__}")
    if value <= 0:
        raise ValueError(f"{name} must be larger than zero, not {value}")


def _check_refresh_rate(refresh_rate):
    """
    Check the refresh rate of Lab.monitor: a finite number of seconds,
    at least _MIN_REFRESH_RATE.

    Examples
    --------
    >>> _check_refresh_rate(5)
    >>> _check_refresh_rate(7.5)
    >>> _check_refresh_rate(1)
    Traceback (most recent call last):
        ...
    ValueError: refresh_rate must be at least 5 seconds, not 1
    >>> _check_refresh_rate(float('nan'))
    Traceback (most recent call last):
        ...
    ValueError: refresh_rate must be at least 5 seconds, not nan
    >>> _check_refresh_rate('10')
    Traceback (most recent call last):
        ...
    TypeError: refresh_rate must be a number, not str
    """
    if not isinstance(refresh_rate, numbers.Real) or isinstance(refresh_rate, bool):
        raise TypeError(f"refresh_rate must be a number, not {type(refresh_rate).__name__}")
    if not (math.isfinite(refresh_rate) and refresh_rate >= _MIN_REFRESH_RATE):
        raise ValueError(f"refresh_rate must be at least {_MIN_REFRESH_RATE} seconds, not {refresh_rate}")


# ----------------------------------------------------------------------
# Doctests

if __name__ == "__main__":
    import doctest
    doctest.testmod(
        extraglobs={},
        verbose=True,
        optionflags=doctest.ELLIPSIS,
    )
