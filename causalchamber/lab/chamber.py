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

# Authors:
#   - Juan L. Gamella [juan@causalchamber.ai]

"""
This module implements the lab.Chamber class for real-time experiments.
"""

# Packages from the standard library
import io
from email import message_from_string
import base64
import numpy as np
import timeit
import threading
import itertools
import time
import sys
import numbers

# Third-party packages
import pandas as pd
from PIL import Image

# Imports from this package
from causalchamber.lab.api import API


class Chamber():
    """
    Interface for operating a Causal Chamber™ in real time..
    
    
    Attributes
    ----------
    chamber_id : str
        The unique chamber identifier.
    model : str
        The model of the chamber, e.g., Light Tunnel Mk2.
    config : str
        Configuration of the chamber.    
    config_version : str
        Version number of the chamber configuration.
    documentation : str
        URL to the documentation for this chamber model and configuration.
    session_id : str
        Unique identifier for the current session (connection).
    verbose : int
        Verbosity level for output messages.
    """
    
    def __init__(self, chamber_id, config, credentials_file, verbose=1):
        """Start a new real-time connection to the specified chamber,
        returning a lab.Chamber instance to control it.
        
        The chamber will reset & verify its hardware, and stop
        attending any other active connections (i.e., instances of
        lab.Chamber)
        
        Parameters
        ----------
        chamber_id : str
            The unique chamber identifier.
        config : str
            Desired configuration of the chamber.
        credentials_file : str
            Path to the configuration file containing API
            credentials. The file should contain the following lines:
            ```
            [api_keys]
            user = <YOUR USERNAME>
            password = <YOUR PASSWORD>
            ```
        verbose : int, optional
            Verbosity level for status messages. 0 for silent, 1 for normal
            output (default is 1).
        
        Raises
        ------
        FileNotFoundError
            If the credentials file does not exist at the specified path.
        UserError
            If credentials are incorrect, or the requested chamber or
            configuration do not exist.        
        LabError
            If no connection to the API can be established or an error
            on our side prevents starting a session with the chamber.
        """
        # Store parameters
        self._chamber_id = chamber_id
        self._config = config
        self._verbose = verbose

        # Load credentials
        self._API = API(credentials_file)

        # Start a session
        if self.verbose:
            print(f"\nContacting chamber {chamber_id}")
            print(f"  Resetting & verifying hardware (config: {config})")
            spinner = _Spinner("    Please wait")
            spinner.start()
            start = timeit.default_timer()

        try:
            response = self._API.make_request('POST', 'sessions', {'chamber_id': chamber_id, 'chamber_config': config})
            self._session_id = response.json()['session_id']
            self._chamber_model = response.json()['chamber_model']
            self._config_version = response.json()['config_version']
            self._documentation = response.json()['documentation']
        finally:
            spinner.stop() if self.verbose else None
            
        if self.verbose:
            print(f"  Done. ({timeit.default_timer() - start:0.2f} seconds)")
            print(self)

    def set(self, target, value):
        """
        Set a chamber variable to the specified value, i.e., sends a
        SET,:target,:value instruction to the chamber.
        
        Parameters
        ----------
        target : str
            Name of the variable to set (e.g., 'load_in', 'red').
        value : float or int
            Value to set the variable to.
        
        Raises
        ------
        TypeError
            If target is not a string.
        UserError        
            If the target does not exist in this chamber/configuration
            or value is invalid (code 400), or if the chamber is
            currently busy restarting or executing other instructoins
            (code 409).
        LabError
            If there is an error on our side, e.g., an internal server
            error, a hardware error or a connection issue.

        """
        instruction = _generate_set(target, value)
        return self._submit_instructions([instruction])

    def measure(self, n, delay=0):
        """Take n successive measurements of all variables in the
        chamber, including images if it produces them. By setting
        delay (in milliseconds), the chamber adds an additional delay
        between measurements.

        This sends a MSR,:n,:delay instruction to the chamber.
        
        Parameters
        ----------
        n : int
            Number of measurements to collect. Must be larger than zero.
        delay : int
            Delay between consecutive measurements in milliseconds. Must be
            non-negative (default is 0).
        
        Returns
        -------
        pandas.DataFrame or tuple of (pandas.DataFrame, list of numpy.ndarray)
            A DataFrame containing the measured observations. If the
            chamber produces images, a tuple with the observations and
            the collected images as a list of numpy arrays.
        
        Raises
        ------
        TypeError
            If n or delay are not numbers.
        ValueError
            If n is not larger than zero or delay is negative.
        UserError        
            Returned if the chamber is currently busy restarting or executing
            other instructions (code 409).
        LabError
            If there is an error on our side, e.g., an internal server
            error, a hardware error or a connection issue.

        """
        instruction = _generate_msr(n, delay)
        return self._submit_instructions([instruction])

    def msr(self, n, delay=0):
        """
        Shorthand alias for the Chamber.measure(..) method. See
        the Chamber.measure(..) documentation for full details.
        """
        return self.measure(n, delay)

    @property
    def verbose(self):
        """
        Get the verbosity level for output messages.
        
        Returns
        -------
        int
            Verbosity level (0 for silent, 1 for normal output).
        """
        return self._verbose
    
    @property
    def session_id(self):
        """
        Get the unique identifier for the current session.
        
        Returns
        -------
        str
            Unique session ID.
        """
        return self._session_id
    
    @property
    def chamber_id(self):
        """
        Get the unique identifier of the Causal Chamber™ to which this lab.Chamber instance is connected.
        
        Returns
        -------
        str
            Unique chamber identifier.
        """
        return self._chamber_id
    
    @property
    def config(self):
        """
        Get the chamber configuration, specified during initialization.
        
        Returns
        -------
        str
            Configuration name.
        """
        return self._config

    @property
    def config_version(self):
        """
        Get the version number of the chamber configuration.
        
        Returns
        -------
        str
            Configuration version.
        """
        return self._config_version

    @property
    def documentation(self):
        """
        Get the URL to the documentation for this chamber model and configuration.
        
        Returns
        -------
        str
            Documentation URL.
        """
        return self._documentation
    
    @property
    def model(self):
        """
        Get the model identifier of the chamber.
        
        Returns
        -------
        str
            Chamber model.
        """
        return self._chamber_model

    def new_batch(self):
        """Create a new batch object to send multiple instructions in
        a single request.

        This saves each instruction the round trip to the chamber,
        lowering the overall execution time, and ensuring the timing
        between instructions is not affected by fluctuations in your
        connection.
        
        Returns
        -------
        Batch
            A new Batch instance associated with this chamber.        
        """
        return Batch(self)

    def _submit_instructions(self, instructions):
        """
        Submit a list of instructions to the API.
        
        Internal method used by the other methods of the class and the Batch object.
        
        Parameters
        ----------
        instructions : list of str
            List of instruction strings to send to the chamber.
        
        Returns
        -------
        None, pandas.DataFrame, or tuple
            Returns None if the response is empty (e.g., WAIT and SET
            instructions). If the response contains data (MSR
            instructions), returns a pandas.DataFrame with the
            collected observations, or a tuple (pandas.Dataframe, list
            of numpy arrays) if the chamber also produces images.
        
        Raises
        ------
        UserError
            If the API returns a client-side error.
        LabError
            If there is a server-side error or connection issue.

        """
        body = {'instructions': instructions}
        response = self._API.make_request('POST', f'sessions/{self.session_id}/instructions', body)
        content_type = response.headers.get('content-type', '')
        # Parse response
        if response.text == '':
            return None
        else:
            obs, images = _parse_multipart_response(response.text, content_type)
            if not images:
                return obs
            else:
                return obs, images

        
    def __str__(self):
        """
        Return a formatted string representation of the chamber.
        
        Returns
        -------
        str
            Multi-line string with the chamber details.
        """
        msg = f"""
    Causal Chamber™ {self.chamber_id}
  ---------------------------------
       chamber_id : {self.chamber_id}
            model : {self.model}
    configuration : {self.config}
          version : {self.config_version}
       session_id : {self.session_id}
         endpoint : {self._API.endpoint}
    documentation : {self.documentation}
        """
        return msg


class Batch():
    """
    Batch object to send multiple instructions in a single request.

    This saves each instruction the round trip to the chamber,
    lowering the overall execution time, and ensuring the timing
    between instructions is not affected by fluctuations in your
    connection.
    
    Builder for batching multiple chamber instructions into a single API request.
        
    Attributes
    ----------
    instructions : list of str
        List of instructions in the batch.
    
    """

    def __init__(self, chamber):
        """
        Initialize a Batch instance associated with the given lab.Chamber object.
        
        Parameters
        ----------
        chamber : lab.Chamber
            The Chamber instance through which this batch submits instructions.
        """
        self._chamber = chamber
        self._instructions = []

    @property
    def instructions(self):
        """
        Get the list instruction in the batch.
        
        Returns
        -------
        list of str
            List of instruction strings that have been added to this batch.

        Examples
        --------
        >>> batch = Batch(None)
        >>> batch.set('red', 192)
        >>> batch.measure(1, 0)
        >>> batch.instructions
        ['SET,red,192.0', 'MSR,1,0']
        """
        return self._instructions
        
    def set(self, target, value):
        """
        Queue a SET instruction to modify a chamber parameter.
        
        Adds a SET instruction to the batch without executing it immediately.
        The instruction will be executed when submit() is called.
        
        Parameters
        ----------
        target : str
            Name of the parameter to set.
        value : float or int
            Value to set the parameter to. Will be converted to float.
        
        Returns
        -------
        None
        
        Raises
        ------
        TypeError
            If target is not a string.
        
        Examples
        --------
        >>> batch = Batch(None)
        >>> batch.set('red', 252)
        >>> batch.set('pol_1', 180)
        """
        instruction = _generate_set(target, value)
        self._instructions.append(instruction)

    def wait(self, milliseconds, limit=30000):
        """Queue a WAIT instruction. The chamber will then wait the
        given milliseconds before executing the next instruction. This
        is useful if we want to add a delay between a set and measure
        instruction.

        The chamber will be busy during this time, i.e., not attend
        other instructions or connection requests, so use with
        care. As a default, there is a limit of 30 seconds (30000 ms)
        which must be manually overriden.
        
        Parameters
        ----------
        milliseconds : int
            Duration to wait in milliseconds. Must be positive.
        limit: int or None
            To avoid accidentally blocking the chamber, if limit is
            not None and milliseconds is above limit, a
            ValueError exception is raised. Setting limit to None
            means no check is performed. Default is 30 seconds (30000
            ms).

        
        Returns
        -------
        None
        
        Raises
        ------
        TypeError
            If milliseconds is not a number.
        ValueError
            If milliseconds is not positive or milliseconds is larger
            than limit.
        
        Examples
        --------
        >>> batch = Batch(None)
        >>> batch.wait(1000)
        >>> batch.wait(500)
        >>> batch.wait(30000)
        
        >>> batch.wait(30001)
        Traceback (most recent call last):
            ...
        ValueError: milliseconds (30001) is larger than the set limit (30000 ms). Set 'limit=None' to override.
        
        >>> batch.wait(30001, limit=None)
        """
        instruction = _generate_wait(milliseconds)
        if limit is not None and milliseconds > limit:
            raise ValueError(f"milliseconds ({milliseconds}) is larger than the set limit ({limit} ms). Set 'limit=None' to override.")
        self._instructions.append(instruction)
        
    def measure(self, n, delay=0):
        """
        Queue a MEASURE instruction to collect sensor observations.
        
        Adds a MEASURE instruction to the batch without executing it immediately.
        The instruction will be executed when submit() is called.
        
        Parameters
        ----------
        n : int
            Number of measurements to collect. Must be positive.
        delay : int or float, optional
            Delay between consecutive measurements in milliseconds (default is 0).
        
        Returns
        -------
        None
        
        Raises
        ------
        TypeError
            If n or delay are not numbers.
        ValueError
            If n is not positive or delay is negative.
        
        Examples
        --------
        >>> batch = Batch(None)
        >>> batch.measure(100)
        >>> batch.measure(50, delay=10)
        """
        instruction = _generate_msr(n, delay)
        self._instructions.append(instruction)

    def msr(self, n, delay=0):
        """
        Shorthand alias for the measure() method. See measure() for a full description.
        
        Examples
        --------
        >>> batch = Batch(None)
        >>> batch.msr(100)
        >>> batch.msr(50, delay=10)
        """
        return self.measure(n, delay)

    def clear(self):
        """
        Clears the list of instructions in the batch.x        
        
        Returns
        -------
        None

        Examples
        --------
        >>> batch = Batch(None)
        >>> batch.set('red', 192)
        >>> batch.measure(1, 0)
        >>> batch.instructions
        ['SET,red,192.0', 'MSR,1,0']
        >>> batch.clear()
        >>> batch.instructions
        []
        """
        self._instructions = []
        
    def submit(self):
        """
        Submit the instructions in the batch to the chamber.

        The list of instructions remains unchanged after this call. You can clear it with .clear() or continue adding instructions.
        
        Returns
        -------
        None, pandas.DataFrame, or tuple
            Returns None if the response is empty (e.g., WAIT and SET
            instructions). If the response contains data (MSR
            instructions), returns a pandas.DataFrame with the
            collected observations, or a tuple (pandas.Dataframe, list
            of numpy arrays) if the chamber also produces images.
        
        Raises
        ------
        UserError
            If the API returns a client-side error, e.g., an invalid
            instruction (code 400) or the chamber is busy restarting
            or executing instructions (409).
        LabError
            If there is a server-side error or connection issue.

        """
        return self._chamber._submit_instructions(self._instructions)
        
    
# --------------------------------------------------------------------
# Auxiliary functions: instruction generators
    
def _generate_set(target, value):
    """
    Generate a SET instruction string.
        
    Parameters
    ----------
    target : str
        Name of the parameter to set.
    value : float or int
        Value to set the parameter to.
    
    Returns
    -------
    str
        Formatted instruction string in the format 'SET,<target>,<value>'.
    
    Raises
    ------
    TypeError
        If target is not a string.
    ValueError
        If the given value could not be converted to float.
    
    Examples
    --------
    >>> _generate_set('red', 240)
    'SET,red,240.0'
    >>> _generate_set('pol_1', 97.1)
    'SET,pol_1,97.1'
    
    >>> _generate_set(123, 97.1)
    Traceback (most recent call last):
        ...
    TypeError: target must be a string, not int
    
    >>> _generate_set('pol_1', '1aw')
    Traceback (most recent call last):
        ...
    ValueError: could not convert string to float: '1aw'
    """
    # Check inputs
    if not isinstance(target, str):
        raise TypeError(f"target must be a string, not {type(target).__name__}")
    # Generate and return
    return f'SET,{target},{float(value)}'

def _generate_msr(n, delay):
    """
    Generate a MSR instruction string.
    
    Parameters
    ----------
    n : int
        Number of measurements to collect. Must be larger than zero.
    delay : int
        Delay between consecutive measurements in milliseconds. Must be non-negative.
    
    Returns
    -------
    str
        Formatted instruction string in the format 'MSR,<n>,<delay>'.
    
    Raises
    ------
    TypeError
        If n or delay are not integers.
    ValueError
        If n is not positive or delay is negative.
    
    Examples
    --------
    >>> _generate_msr(100, 0)
    'MSR,100,0'
    >>> _generate_msr(50, 10)
    'MSR,50,10'

    >>> _generate_msr(100.0, 0)
    Traceback (most recent call last):
        ...
    TypeError: n must be an integer larger than zero, not float
    
    >>> _generate_msr(0, 0)
    Traceback (most recent call last):
        ...
    ValueError: n must be an integer larger than zero
    
    >>> _generate_msr(-1, 0)
    Traceback (most recent call last):
        ...
    ValueError: n must be an integer larger than zero

    >>> _generate_msr(100, 0.0)
    Traceback (most recent call last):
        ...
    TypeError: delay must be a non-negative integer, not float
    
    >>> _generate_msr(1, -1)
    Traceback (most recent call last):
        ...
    ValueError: delay must be a non-negative integer
    """
    # Check inputs: n
    error_msg = "n must be an integer larger than zero"
    if not isinstance(n, numbers.Integral):
        raise TypeError(f"{error_msg}, not {type(n).__name__}")
    if n <= 0:
        raise ValueError(error_msg)

    # Check inputs: delay
    error_msg = "delay must be a non-negative integer"
    if not isinstance(delay, numbers.Integral):
        raise TypeError(f"{error_msg}, not {type(delay).__name__}")
    if delay < 0:
        raise ValueError(error_msg)
    # Generate and return
    return f'MSR,{n},{delay}'


def _generate_wait(milliseconds):
    """
    Generate a WAIT instruction string.
    
    
    Parameters
    ----------
    milliseconds : int
        Duration to wait in milliseconds. Must be positive.
    
    Returns
    -------
    str
        Formatted instruction string in the format 'WAIT,<milliseconds>'.
    
    Raises
    ------
    TypeError
        If milliseconds is not an integer.
    ValueError
        If milliseconds is not larger than zero.
    
    Examples
    --------
    >>> _generate_wait(1000)
    'WAIT,1000'
    >>> _generate_wait(500)
    'WAIT,500'

    >>> _generate_wait(500.0)
    Traceback (most recent call last):
        ...
    TypeError: milliseconds must be an integer larger than zero, not float
    
    >>> _generate_wait(0)
    Traceback (most recent call last):
        ...
    ValueError: milliseconds must be an integer larger than zero
    
    >>> _generate_wait(-2)
    Traceback (most recent call last):
        ...
    ValueError: milliseconds must be an integer larger than zero
    """
    # Check input
    error_msg = "milliseconds must be an integer larger than zero"
    if not isinstance(milliseconds, numbers.Integral):
        raise TypeError(f"{error_msg}, not {type(milliseconds).__name__}")
    if milliseconds <= 0:
        raise ValueError(error_msg)
    # Generate and return
    return f'WAIT,{milliseconds}'
    
# --------------------------------------------------------------------
# Auxiliary functions
              
def _parse_multipart_response(content, content_type):
    """
    Parse a multipart HTTP response containing CSV data and images.
    
    The CSV data is parsed into a pandas.DataFrame, and JPEG images
    are converted to numpy arrays.
    
    Parameters
    ----------
    content : str
        Raw content of the multipart response.
    content_type : str
        Content-Type header value, which must include a boundary parameter.
    
    Returns
    -------
    tuple
        A tuple of (pandas.DataFrame or None, list of numpy.ndarray).
        The DataFrame contains the observational data (or None if no CSV was
        present). The list contains images as numpy arrays (empty list if no
        images were present).
    
    Raises
    ------
    ValueError
        If no boundary is found in the content_type header.
    
    Examples
    --------
    # TODO: add some fixed content to the doctest environment and test this
    # >>> content_type = 'multipart/mixed; boundary=boundary123'
    # >>> data, images = _parse_multipart_response(content, content_type)
    # >>> type(data)
    # <class 'pandas.core.frame.DataFrame'>
    # >>> len(images)
    # 2

    """
    # Extract boundary from content-type header
    boundary = None
    if 'boundary=' in content_type:
        boundary = content_type.split('boundary=')[1].strip()
    
    if not boundary:
        raise ValueError("No boundary found in content-type header")
    
    # Parse the multipart message
    # Add headers to make it a proper email message for parsing
    message_text = f"Content-Type: {content_type}\r\n\r\n{content}"
    msg = message_from_string(message_text)
    
    csv_data = None
    images = []
    
    # Process each part
    for part in msg.walk():
        content_type = part.get_content_type()
        content_disposition = part.get('Content-Disposition', '')
        
        if content_type == 'text/csv':
            # Extract CSV data
            csv_content = part.get_payload()
            csv_data = pd.read_csv(io.StringIO(csv_content))
            
        elif content_type == 'image/jpeg':
            # Extract image data
            img_content = part.get_payload()
            
            # Check if content is base64 encoded
            transfer_encoding = part.get('Content-Transfer-Encoding', '')
            if transfer_encoding == 'base64':
                img_content = base64.b64decode(img_content)
            elif isinstance(img_content, str):
                # If it's a string, it might be base64 encoded
                try:
                    img_content = base64.b64decode(img_content)
                except:
                    # If base64 decode fails, treat as raw bytes
                    img_content = img_content.encode()
            
            # Load image using PIL
            img = Image.open(io.BytesIO(img_content))
            images.append(np.array(img))
    
    return csv_data, images

class _Spinner():
    """
    Simple console spinner animation.
        
    Attributes
    ----------
    _stop_spinner : threading.Event
        Event used to signal the spinner thread to stop.
    _spinner_thread : threading.Thread
        Thread running the spinner animation.
    
    Examples
    --------

    stdout is redirected so this doctest can run

    >>> import sys
    >>> from io import StringIO
    >>> sys.stdout = StringIO() 
    
    >>> spinner = _Spinner("This is a test")
    >>> spinner.start()
    >>> time.sleep(2)
    >>> spinner.stop()
    ...
    """

    def __init__(self, message, symbols = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']):
        """
        Initialize a Spinner instance.
        
        Parameters
        ----------
        message : str
            Message to display next to the spinner animation.
        symbols : list of str, optional
            List of characters to use for the spinner animation. Default is
            a set of Braille characters that create a rotating effect.
        """
        # Define animation
        def spinner_animation(stop_event, message):
            spinner = itertools.cycle(symbols)
            while not stop_event.is_set():
                sys.stdout.write(f'\r{message} {next(spinner)}')
                sys.stdout.flush()
                time.sleep(0.1)
                sys.stdout.write('\r' + ' ' * (len(message) + 2) + '\r')
                sys.stdout.flush()
        # Store thread and stop event
        self._stop_spinner = threading.Event()
        self._spinner_thread = threading.Thread(target=spinner_animation,
                                               args=(self._stop_spinner, message))
        
    def start(self):
        """
        Start the spinner animation.
        
        Begins displaying the spinner animation in the console. This method
        is non-blocking and returns immediately while the animation continues
        in a background thread.
        
        Returns
        -------
        None
        """
        self._spinner_thread.start()

    def stop(self):
        """
        Stop the spinner animation.
        
        Signals the spinner thread to stop and waits for it to complete. Clears
        the spinner from the console, leaving only the original message.
        
        Returns
        -------
        None
        """
        self._stop_spinner.set()
        self._spinner_thread.join()



# ----------------------------------------------------------------------
# Doctests

if __name__ == "__main__":
    import doctest
    doctest.testmod(
        extraglobs={},
        verbose=True,
        optionflags=doctest.ELLIPSIS,
    )
