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

"""Unit tests for causalchamber.lab.api, with the requests to the API
mocked (see causalchamber.lab.test.mocks).
"""

# Packages from the standard library
import contextlib
import io
import unittest

# Third party libraries
import requests

# Imports from this package
from causalchamber.lab.api import API
from causalchamber.lab.exceptions import LabError, UserError
from causalchamber.lab.test.mocks import response, patch_request

ENDPOINT = 'https://api.example.com/v1'
SUPPORT = 'If the problem persists, contact us at support@causalchamber.ai or through any of the provided support channels.'


class MakeRequestTests(unittest.TestCase):

    def setUp(self):
        # Trailing slash, to check that endpoint and path are joined with a single one
        self.api = API(credentials=('user', 'password'), endpoint=ENDPOINT + '/')

    def test_success_returns_response(self):
        with patch_request(response(200, {'account': {'user_id': 'user'}})) as request:
            result = self.api.make_request('GET', '/account')
        self.assertEqual(result.json(), {'account': {'user_id': 'user'}})
        call = request.call_args.kwargs
        self.assertEqual(call['method'], 'GET')
        self.assertEqual(call['url'], ENDPOINT + '/account')
        self.assertEqual(call['auth'], ('user', 'password'))
        self.assertIsNone(call['json'])
        self.assertIsNone(call['params'])

    def test_body_and_query(self):
        with patch_request(response(200, {}), response(200, {})) as request:
            self.api.make_request('POST', 'experiments', {'chamber_id': 'lt-1'})
            self.api.make_request('GET', 'experiments', query={'limit': 5})
        first, second = request.call_args_list
        self.assertEqual(first.kwargs['json'], {'chamber_id': 'lt-1'})
        self.assertEqual(second.kwargs['params'], {'limit': 5})

    def test_put(self):
        with patch_request(response(200, {})) as request:
            self.api.make_request('PUT', 'chambers/lt-1/mode', {'mode': 'queue'})
        call = request.call_args.kwargs
        self.assertEqual((call['method'], call['url'], call['json']),
                         ('PUT', ENDPOINT + '/chambers/lt-1/mode', {'mode': 'queue'}))

    def test_client_errors_raise_user_error(self):
        for code in [400, 401, 402, 403, 409, 422]:
            with self.subTest(code=code):
                body = {'message': 'Rejected', 'request_id': 'r1', 'scheduler_id': 's1'}
                with patch_request(response(code, body)):
                    with self.assertRaises(UserError) as cm:
                        self.api.make_request('POST', 'experiments', {'chamber_id': 'lt-1'})
                e = cm.exception
                self.assertEqual((e.code, e.message, e.request_id, e.scheduler_id),
                                 (code, 'Rejected', 'r1', 's1'))

    def test_other_errors_raise_lab_error(self):
        # Including 404, which points to an unknown URL unless not_found is given
        for code in [404, 405, 415, 500, 503]:
            with self.subTest(code=code):
                with patch_request(response(code, {'message': 'Failed', 'scheduler_id': 's1'})):
                    with self.assertRaises(LabError) as cm:
                        self.api.make_request('GET', 'wrong_path')
                e = cm.exception
                self.assertEqual((e.code, e.message, e.scheduler_id), (code, 'Failed', 's1'))

    def test_not_found_raises_user_error(self):
        message = "Experiment 'abc' does not exist or does not belong to you."
        body = {'message': 'The requested URL does not exist.', 'scheduler_id': 's1'}
        with patch_request(response(404, body)):
            with self.assertRaises(UserError) as cm:
                self.api.make_request('GET', 'experiments/abc', not_found=message)
        e = cm.exception
        self.assertEqual((e.code, e.message, e.scheduler_id), (404, message, 's1'))

    def test_not_found_ignored_for_other_codes(self):
        with patch_request(response(500, {'message': 'Failed'})):
            with self.assertRaises(LabError):
                self.api.make_request('GET', 'experiments/abc', not_found="Not found")

    def test_error_without_json_body(self):
        with patch_request(response(502, b'<html>Bad Gateway</html>')):
            with self.assertRaises(LabError) as cm:
                self.api.make_request('GET', 'account')
        self.assertEqual(cm.exception.code, 502)
        self.assertTrue(cm.exception.message.startswith('There was an error on our side.'))

    def test_connection_error(self):
        with patch_request(requests.exceptions.ConnectionError('Connection refused')):
            with self.assertRaises(LabError) as cm:
                self.api.make_request('GET', 'account')
        self.assertEqual(cm.exception.code, 1)
        self.assertEqual(cm.exception.message,
                         f'Could not connect to the API at {ENDPOINT}/. {SUPPORT} Error details: Connection refused')

    def test_other_request_exception(self):
        with patch_request(requests.exceptions.Timeout('Read timed out')):
            with self.assertRaises(LabError) as cm:
                self.api.make_request('GET', 'account')
        self.assertEqual(cm.exception.code, 1)
        self.assertEqual(cm.exception.message,
                         f'The request to the API at {ENDPOINT}/ failed. {SUPPORT} Error details: Read timed out')


class TimingStatsTests(unittest.TestCase):

    def test_print_timing_stats(self):
        api = API(credentials=('user', 'password'), endpoint=ENDPOINT)
        # Failed requests (with a response) are also timed
        with patch_request(response(200, elapsed=0.1), response(200, elapsed=0.2),
                           response(200, elapsed=0.3), response(401, elapsed=0.5)):
            for _ in range(3):
                api.make_request('GET', 'account')
            with self.assertRaises(UserError):
                api.make_request('POST', 'sessions', {})
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            api.print_timing_stats()
        # Compare the lines, ignoring indentation and blank lines
        lines = [line.strip() for line in output.getvalue().splitlines() if line.strip()]
        self.assertEqual(lines, [
            'Request stats',
            '-------------',
            f'GET {ENDPOINT}/account',
            'total calls: 3',
            'resp. time (avg): 0.2000 seconds',
            'resp. time (std): 0.1000 seconds',
            f'POST {ENDPOINT}/sessions',
            'total calls: 1',
            'resp. time (avg): 0.5000 seconds',
            'resp. time (std): NA seconds',
        ])


if __name__ == '__main__':
    unittest.main()
