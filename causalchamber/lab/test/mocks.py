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

"""This module contains mocks to test the Remote Lab client (in
doctests and unit tests) without contacting the API.
"""

# Packages from the standard library
import json
from datetime import timedelta
from unittest import mock

# Third party libraries
import requests


def response(status_code=200, body=None, headers=None, elapsed=0.1):
    """
    Return a requests.Response as the API would send it.

    Parameters
    ----------
    status_code : int, optional
        The HTTP status code. Default is 200.
    body : dict, list, str, bytes or None, optional
        The body of the response. Bytes are taken as they are, None
        is an empty body, and anything else is encoded as JSON (and
        the Content-Type header set accordingly).
    headers : dict or None, optional
        Additional headers of the response.
    elapsed : float, optional
        The response time, in seconds. Default is 0.1.

    Returns
    -------
    requests.Response

    """
    r = requests.Response()
    r.status_code = status_code
    if body is None:
        r._content = b''
    elif isinstance(body, bytes):
        r._content = body
    else:
        r._content = json.dumps(body).encode()
        r.headers['Content-Type'] = 'application/json'
    r.headers.update(headers or {})
    r.elapsed = timedelta(seconds=elapsed)
    return r


def patch_request(*outcomes):
    """
    Patch requests.request so that its successive calls return the
    given responses or raise the given exceptions, in order.

    Use it as a context manager; it returns the mock, whose
    call_args hold the arguments of the last request.

    """
    return mock.patch('requests.request', side_effect=list(outcomes))

