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

"""This module contains the exceptions raised by the different
functionality of causalchamber.lab

To enable appropriate error handling, the exception hierarchy
distinguishes between server-side errors (LabError) and client-side
errors (UserError).
"""

# Third party libraries
import requests

class _BaseError(Exception):
    """
    Base error class, inherited by LabError and UserError.

    Attributes
    ----------
    code : str or int
        Error code for programmatic error identification
    message : str
        Human-readable error description
    request_id : str
        Unique identifier of the request on the chamber server.
    scheduler_id : str
        Unique identifier of the request on the scheduler.
    """

    def __init__(self, code, message, request_id=None, scheduler_id=None):
        """
        Initialize a LabError exception.
        
        Parameters
        ----------
        code : int
            Numeric error code identifying the specific error type
        message : str
            Descriptive error message explaining what went wrong
        request_id : str
            Unique identifier of the request on the chamber server.
        scheduler_id : str
            Unique identifier of the request on the scheduler.
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.request_id = request_id
        self.scheduler_id = scheduler_id

    @classmethod
    def from_response(cls, response):
        """Initialize using a requests.Response object.

        Parameters
        ----------
        response: requests.Response
            The response to an HTTP request from which to take the
            code (HTTP status code), and message, request_id and
            scheduler_id from the JSON body (if they exist).

        """
        # Check input
        if not isinstance(response, requests.Response):
            raise TypeError(f"response must be an instance of requests.Response, not {type(response).__name__}")
        # Try to parse json body
        try:
            params = response.json()
        except Exception:
            params = {}
        # Build exception
        return cls(code = response.status_code,
                   message = params.get('message', None),
                   request_id = params.get('request_id', None),
                   scheduler_id = params.get('scheduler_id', None))
        
    def __str__(self):
        """
        Return a formatted string representation of the error.
        
        Returns
        -------
        str
            Formatted error string including code and message
        """
        return f"(code {self.code}) {self.message}\n  Trace codes\n      (chamber: {self.request_id})\n    (scheduler: {self.scheduler_id})"

class LabError(_BaseError):
    """
    Exceptions raised by errors on our side, i.e., for which the user is not responsible.
    
    This exception indicates internal issues with the Remote Lab, such
    as hardware malfunctions, server errors, or backend processing
    failures. These errors typically require intervention from the
    system administrators rather than changes to user code.

    If such errors arise, you can reach out to us at support@causalchamber.ai

    Attributes
    ----------
    code : str or int
        Error code for programmatic error identification
    message : str
        Human-readable error description
    request_id : str
        Unique identifier of the request on the chamber server.
    scheduler_id : str
        Unique identifier of the request on the scheduler.
    """
    def __init__(self, code, message, request_id=None, scheduler_id=None):
        # Set a default message if it is not provided
        if message is None:
            message = 'There was an error on our side. Please try again. If the problem persists, please contact us at support@causalchamber.ai or through any of the provided support channels.'
        super().__init__(code, message, request_id, scheduler_id)
                 
    
class UserError(_BaseError):
    """
    Exceptions raised by errors on the side of the user. For
    example, when the user provided invalid input.

    These errors can typically be resolved by correcting the user's
    code or input parameters.
    
    Attributes
    ----------
    code : str or int
        Error code for programmatic error identification
    message : str
        Human-readable error description with guidance for resolution
    request_id : str
        Unique identifier of the request on the chamber server.
    scheduler_id : str
        Unique identifier of the request on the scheduler.

    """
