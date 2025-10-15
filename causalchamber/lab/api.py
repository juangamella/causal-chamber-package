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

"""This module contains the common API access logic underlying the
other classes in .lab. Authentication and error handling is
implemented here.
"""

# Packages from the standard library
import configparser
import statistics
import os

# Third party libraries
import requests

# Imports from this package
from causalchamber.lab.exceptions import LabError, UserError


class API():
    """
    API client for interacting with the Remote Lab API from Causal Chamber™.
    
    The class handles authentication and HTTP requests to the API. It manages
    credentials, tracks request timing statistics, and provides error handling
    for various response codes.
    
    Attributes
    ----------
    endpoint : str
        Base URL for the API endpoint.
    """

    def __init__(self, credentials_file, endpoint='https://api.causalchamber.ai/v0'):
        """
        Initialize the API client with credentials and endpoint.
        
        Reads authentication credentials from a configuration file and sets up
        the API client with the specified endpoint URL. Also initializes an
        internal dictionary to track timing statistics for API requests.
        
        Parameters
        ----------
        credentials_file : str

            Path to the configuration file containing API
            credentials. The file should contain the following lines:
            ```
            [api_keys]
            user = <YOUR USERNAME>
            password = <YOUR PASSWORD>
            ```
        endpoint : str, optional
            Base URL for the API endpoint. Default is 
            'https://api.causalchamber.ai/v0'.
        
        Raises
        ------
        lab.exceptions.UserError
            If the credentials file does not contain the required 'api_keys'
            section or 'user' and 'password' fields.
        FileNotFoundError
            If the credentials file does not exist at the specified path.
        
        Examples
        --------
        >>> api = API('credentials_example.ini')
        >>> api = API('credentials_example.ini', endpoint='https://custom.api.com/v1')
       
        >>> api = API('causalchamber/lab/test/malformed_credentials_1')
        Traceback (most recent call last):
        ...
        causalchamber.lab.exceptions.UserError: (code 0) Could not find entry 'password' in credentials file...

        >>> api = API('causalchamber/lab/test/malformed_credentials_2')
        Traceback (most recent call last):
        ...
        causalchamber.lab.exceptions.UserError: (code 0) Could not find entry 'user' in credentials file...

        >>> api = API('causalchamber/lab/test/malformed_credentials_3')
        Traceback (most recent call last):
        ...
        causalchamber.lab.exceptions.UserError: (code 0) Could not find header '[api_keys]'...

        >>> api = API('nonexistent_credentials_file.ini')
        Traceback (most recent call last):
        ...
        FileNotFoundError: No credentials file found at the path you provided...
        """
        self._stats_timing = {}  # timing dictionary
        self._endpoint = endpoint
        # Read credentials file
        if not os.path.exists(credentials_file):
            raise FileNotFoundError(f"No credentials file found at the path you provided: '{credentials_file}'")
        credentials = configparser.ConfigParser()
        try:
            credentials.read(credentials_file)
            self._api_user = credentials['api_keys']['user']
            self._api_password = credentials['api_keys']['password']
        except KeyError as e:
            raise UserError(0, f"Could not find entry '{e.args[0]}' in credentials file at '{credentials_file}'. Check your credentials file and try again.")
        except configparser.MissingSectionHeaderError:
            raise UserError(0, f"Could not find header '[api_keys]' in credentials file at '{credentials_file}'. Check your credentials file and try again.")

    @property
    def endpoint(self):
        """
        Get the API endpoint URL.
        
        Returns
        -------
        str
            The base URL for the API endpoint.
        """
        return self._endpoint
        
    def make_request(self, method, path, parameters=None):
        """Make an HTTP request to the API endpoint.
        
        Sends an authenticated HTTP request to the API and handles various
        response codes. Automatically tracks timing statistics for each request.
        The method constructs the full URL by combining the endpoint with the
        provided path and sends the parameters as JSON in the request body.
        
        Parameters
        ----------
        method : str
            HTTP method to use. Must be either 'GET' or 'POST'.
        path : str
            API path to append to the base endpoint (e.g., '/data', '/models').
            Leading/trailing slashes are handled automatically.
        parameters : dict or None, optional
            Dictionary of parameters to send as JSON body in the
            request. If None, the request is made with an empty
            body. Default is None
        
        Returns
        -------
        requests.Response
            Response object from the API request if successful (status code 200).
        
        Raises
        ------
        ValueError
            If method is not 'GET' or 'POST'.
        UserError
            If the API returns a 400, 401, 403 or 409 HTTP error, indicating a
            client-side error.
        LabError
            If it is impossible to connect to the API, or the API
            returns any other HTTP code, including error codes (e.g.,
            404, 405 and 5XX) which indicate a server error or point
            to a potential error in this client.
        
        Examples
        --------
        >>> api = API('credentials_example.ini')
        >>> api.make_request('POST', 'sessions/', None)
        Traceback (most recent call last):
        ...
        causalchamber.lab.exceptions.UserError: (code 401) ...

        >>> api = API('credentials_example.ini', endpoint='https://api.causalchamber.ai')
        >>> response = api.make_request('GET', '/health', None)
        >>> response.status_code
        200

        >>> api.make_request('POST', '/health', {'experiment_id': '123'})
        Traceback (most recent call last):
        ...
        causalchamber.lab.exceptions.LabError: (code 405) ...

        >>> api.make_request('POST', '/wrong_path', {'experiment_id': '123'})
        Traceback (most recent call last):
        ...
        causalchamber.lab.exceptions.LabError: (code 404) ...

        """
        if method not in ['GET', 'POST']:
            raise ValueError(f"HTTP method '{method}' is not allowed")
        
        # Ensure there's a single '/' between endpoint and path
        url = self._endpoint.rstrip('/') + '/' + path.lstrip('/')

        try:
            response = requests.request(
                method=method,
                url=url,
                json=parameters,
                auth=(self._api_user, self._api_password)
            )
        except requests.exceptions.ConnectionError:
            raise LabError(1, f'Could not connect to the API at {self.endpoint}. Please try again. If the problem persists, please contact us at support@causalchamber.ai')

        # Store request roundtime in stats dictionary
        key = f'{method} {url}'
        if key not in self._stats_timing:
            self._stats_timing[key] = []
        self._stats_timing[key].append(response.elapsed.total_seconds())

        # Return succesful requests
        if response.status_code == 200:
            return response

        # Otherwise, parse the error codes            
        if response.status_code in [400, 401, 403, 409]:
            raise UserError.from_response(response)
        else:
            raise LabError.from_response(response)

    def print_timing_stats(self):
        """
        Print timing statistics for all API requests made, grouped by HTTP method and URL.
        
        Returns
        -------
        None
            Prints statistics directly to stdout.
        
        Notes
        -----
        Standard deviation is only calculated when there are 2 or more calls
        to the same endpoint. For single calls, 'NA' is displayed instead.
        
        Examples
        --------
        >>> api = API('credentials_example.ini', endpoint='https://api.causalchamber.ai')
        >>> _ = api.make_request('GET', '/health', {})
        >>> _ = api.make_request('GET', '/health', {})
        >>> _ = api.make_request('GET', '/health', {})
        >>> api.make_request('POST', 'v0/sessions', {})
        Traceback (most recent call last):
        ...
        causalchamber.lab.exceptions.UserError: (code 401) ...
        >>> api.print_timing_stats()
        Request stats
        -------------
        <BLANKLINE>
        <BLANKLINE>
                      GET https://api.causalchamber.ai/health
                             total calls: 3
                        resp. time (avg): ... seconds
                        resp. time (std): ... seconds
        <BLANKLINE>
        <BLANKLINE>
                      POST https://api.causalchamber.ai/v0/sessions
                             total calls: 1
                        resp. time (avg): ... seconds
                        resp. time (std): NA seconds
        <BLANKLINE>
        """
        print("Request stats")
        print("-------------")
        print()
        
        for key, timings in self._stats_timing.items():
            total_calls = len(timings)
            # Calculate statistics
            avg_time = f'{statistics.mean(timings):0.4f}'
            std_time = f'{statistics.stdev(timings):0.4f}' if total_calls > 1 else 'NA'
            string = f"""
              {key}
                     total calls: {total_calls}
                resp. time (avg): {avg_time} seconds
                resp. time (std): {std_time} seconds
            """
            print(string)


# ----------------------------------------------------------------------
# Doctests

if __name__ == "__main__":
    import doctest
    doctest.testmod(
        extraglobs={},
        verbose=True,
        optionflags=doctest.ELLIPSIS,
    )
