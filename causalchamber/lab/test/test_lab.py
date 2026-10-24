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

"""Unit tests for causalchamber.lab.lab and the session handling of
causalchamber.lab.chamber, with the requests to the API mocked (see
causalchamber.lab.test.mocks). The response bodies are the examples
of the API specification (causalchamber/lab/swagger.yaml).
"""

# Packages from the standard library
import contextlib
import io
import unittest
from unittest import mock

# Imports from this package
from causalchamber.lab.chamber import Chamber
from causalchamber.lab.exceptions import LabError, UserError
from causalchamber.lab.lab import Lab, Protocol, Session
from causalchamber.lab.test.mocks import response, patch_request

ENDPOINT = 'https://api.example.com/v1'
CREDENTIALS = ('user123', 'password')

# --------------------------------------------------------------------
# Response bodies (from the examples in the API specification)

ACCOUNT = {
    'user_id': 'user123', 'email': 'user123@example.com', 'name': 'Ada Lovelace',
    'institution': 'ETH Zurich', 'requested_academic': True, 'is_academic': True,
    'wallet': {'wallet_id': 'wallet_8f14e45f', 'credits': 3600, 'credit_floor': 0},
    'sessions': [], 'experiments': [], 'chambers': [],
}

EXPERIMENT = {
    'experiment_id': 'f47ac10b-58cc-4372-a567-0e02b2c3d479', 'chamber_id': 'tt-test-virt',
    'chamber_config': 'standard', 'status': 'QUEUED', 'user_id': 'user123', 'tag': 'baseline_test',
    'submitted_on': 1709856000.123, 'started_on': None, 'est_runtime_seconds': 66.0,
    'total_instructions': 3, 'current_instruction': None, 'download_url': None, 'checksum': None,
}

CHAMBER = {
    'chamber_id': 'tt-test-virt', 'chamber_model': 'Dummy Chamber Mk1', 'mode': 'queue',
    'chamber_state': 'busy', 'available_on': 1709859820.456,
    'configs': [{'chamber_config': 'standard', 'config_version': '1.0',
                 'docs': 'http://box.causalchamber.ai/config_doc_tt_mk1_standard.pdf'}],
    'queue': [dict(EXPERIMENT, status='RUNNING', position=0, started_on=1709856100.456,
                   current_instruction=1)],
    'session': None,
}

SESSION_ID = 'a778b917-7a05-4b6c-bca7-58805cc1e971'

SESSION = {
    'session_id': SESSION_ID, 'chamber_id': 'tt-test-virt', 'chamber_config': 'standard',
    'user_id': 'user123', 'started_on': 1760000000.123, 'expires_on': 1760003600.123,
    'duration_seconds': 3600,
}

STARTED_SESSION = dict(SESSION, chamber_model='Dummy Chamber Mk1', chamber_status='READY',
                       config_version='1.0', valid_configs=['standard', 'camera'],
                       codebase_version='3f2a9c1', documentation=None,
                       request_id='6ba7b810-9dad-11d1-80b4-00c04fd430c8')

STOPPED_SESSION = dict(SESSION, refund=3000, unused_seconds=3000.512)

NOT_FOUND = {'message': 'The requested URL does not exist.', 'scheduler_id': 's1'}
NOT_ACTIVE = {'message': f"Session '{SESSION_ID}' has been stopped, has expired, or has been superseded by another session.",
              'scheduler_id': 's1'}


def ok(**body):
    """Return a successful response with the given fields (and a scheduler_id)."""
    return response(200, dict(body, scheduler_id='550e8400-e29b-41d4-a716-446655440000'))


def make_lab():
    """Return a Lab, logged in with a mocked account."""
    with patch_request(ok(account=ACCOUNT)):
        return Lab(credentials=CREDENTIALS, endpoint=ENDPOINT, verbose=False)


def captured_stdout(function, *args, **kwargs):
    """Call the function, returning its result and what it printed."""
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        result = function(*args, **kwargs)
    return result, output.getvalue()


# --------------------------------------------------------------------
# Tests

class LoginTests(unittest.TestCase):

    def test_init_fetches_account(self):
        with patch_request(ok(account=ACCOUNT)) as request:
            Lab(credentials=CREDENTIALS, endpoint=ENDPOINT, verbose=False)
        call = request.call_args.kwargs
        self.assertEqual((call['method'], call['url'], call['auth']),
                         ('GET', ENDPOINT + '/account', CREDENTIALS))

    def test_init_prints_dashboard_if_verbose(self):
        # A single request both checks the credentials and gets the dashboard
        with patch_request(ok(account=ACCOUNT)) as request, \
             mock.patch('causalchamber.lab.lab.print_dashboard') as print_dashboard:
            Lab(credentials=CREDENTIALS, endpoint=ENDPOINT, verbose=True)
        print_dashboard.assert_called_once_with(ACCOUNT)
        self.assertEqual(request.call_count, 1)

    def test_init_does_not_print_if_not_verbose(self):
        with patch_request(ok(account=ACCOUNT)) as request, \
             mock.patch('causalchamber.lab.lab.print_dashboard') as print_dashboard:
            Lab(credentials=CREDENTIALS, endpoint=ENDPOINT, verbose=False)
        print_dashboard.assert_not_called()
        self.assertEqual(request.call_count, 1)

    def test_dashboard(self):
        lab = make_lab()
        updated = dict(ACCOUNT, name='New')
        with patch_request(ok(account=updated)) as request, \
             mock.patch('causalchamber.lab.lab.print_dashboard') as print_dashboard:
            lab.dashboard()
        print_dashboard.assert_called_once_with(updated)
        self.assertEqual(request.call_args.kwargs['url'], ENDPOINT + '/account')

    def test_get_account(self):
        lab = make_lab()
        with patch_request(ok(account=ACCOUNT)):
            self.assertEqual(lab.get_account(), ACCOUNT)


PAYMENT_LINKS = {'invoice': 'To pay via invoice or through a purchase order from your institution, please write us at support@causalchamber.ai'}


class TopupTests(unittest.TestCase):

    def test_topup(self):
        lab = make_lab()
        with patch_request(ok(payment_links=PAYMENT_LINKS)) as request, \
             mock.patch('causalchamber.lab.lab.print_topup') as print_topup:
            self.assertEqual(lab.topup(), PAYMENT_LINKS)
        # The wallet is the one of the account fetched on login
        call = request.call_args.kwargs
        self.assertEqual((call['method'], call['url'], call['json']),
                         ('POST', ENDPOINT + '/wallet/wallet_8f14e45f/topup', None))
        print_topup.assert_called_once_with(PAYMENT_LINKS)

    def test_topup_not_verbose(self):
        lab = make_lab()
        with patch_request(ok(payment_links=PAYMENT_LINKS)), \
             mock.patch('causalchamber.lab.lab.print_topup') as print_topup:
            lab.topup(verbose=False)
        print_topup.assert_not_called()

    def test_wallet_updated_with_account(self):
        lab = make_lab()
        account = dict(ACCOUNT, wallet=dict(ACCOUNT['wallet'], wallet_id='wallet_new'))
        with patch_request(ok(account=account), ok(payment_links=PAYMENT_LINKS)) as request:
            lab.get_account()
            lab.topup(verbose=False)
        self.assertEqual(request.call_args.kwargs['url'], ENDPOINT + '/wallet/wallet_new/topup')

    def test_wallet_changed(self):
        lab = make_lab()
        with patch_request(response(404, NOT_FOUND)):
            with self.assertRaises(UserError) as cm:
                lab.topup(verbose=False)
        self.assertEqual(cm.exception.code, 404)
        self.assertIn("Please log in again", cm.exception.message)


class MonitorTests(unittest.TestCase):

    def test_runs_monitor(self):
        lab = make_lab()
        with mock.patch('causalchamber.lab.lab.run_monitor') as run_monitor:
            lab.monitor(refresh_rate=10)
        run_monitor.assert_called_once_with(lab.get_account, 10)

    def test_invalid_refresh_rate(self):
        lab = make_lab()
        with mock.patch('causalchamber.lab.lab.run_monitor') as run_monitor:
            with self.assertRaises(ValueError):
                lab.monitor(refresh_rate=4.9)
            with self.assertRaises(TypeError):
                lab.monitor(refresh_rate='5')
        run_monitor.assert_not_called()


class ChamberTests(unittest.TestCase):

    def test_get_chamber(self):
        lab = make_lab()
        with patch_request(ok(chamber=CHAMBER)) as request:
            chamber = lab.get_chamber('tt-test-virt', verbose=False)
        self.assertEqual(chamber, CHAMBER)
        call = request.call_args.kwargs
        self.assertEqual((call['method'], call['url']), ('GET', ENDPOINT + '/chambers/tt-test-virt'))

    def test_get_chamber_prints_if_verbose(self):
        lab = make_lab()
        with patch_request(ok(chamber=CHAMBER)), \
             mock.patch('causalchamber.lab.lab.print_chamber') as print_chamber:
            lab.get_chamber('tt-test-virt', print_max=3)
        print_chamber.assert_called_once_with(CHAMBER, 'user123', print_max=3)

    def test_get_chamber_not_found(self):
        lab = make_lab()
        with patch_request(response(404, NOT_FOUND)):
            with self.assertRaises(UserError) as cm:
                lab.get_chamber('lt-other', verbose=False)
        self.assertEqual(cm.exception.code, 404)
        self.assertEqual(cm.exception.message, "Chamber 'lt-other' does not exist or you do not have access to it.")

    def test_get_chamber_invalid_arguments(self):
        lab = make_lab()
        with patch_request() as request:
            with self.assertRaises(TypeError):
                lab.get_chamber(1)
            with self.assertRaises(ValueError):
                lab.get_chamber('tt-test-virt', print_max=0)
        request.assert_not_called()

    def test_get_queue_is_get_chamber(self):
        lab = make_lab()
        with patch_request(ok(chamber=CHAMBER)) as request:
            self.assertEqual(lab.get_queue('tt-test-virt', verbose=False), CHAMBER)
        self.assertEqual(request.call_args.kwargs['url'], ENDPOINT + '/chambers/tt-test-virt')


class ExperimentTests(unittest.TestCase):

    def test_get_experiment(self):
        lab = make_lab()
        with patch_request(ok(experiment=EXPERIMENT)) as request:
            self.assertEqual(lab.get_experiment(EXPERIMENT['experiment_id']), EXPERIMENT)
        call = request.call_args.kwargs
        self.assertEqual((call['method'], call['url']),
                         ('GET', f"{ENDPOINT}/experiments/{EXPERIMENT['experiment_id']}"))

    def test_get_experiment_not_found(self):
        lab = make_lab()
        with patch_request(response(404, NOT_FOUND)):
            with self.assertRaises(UserError) as cm:
                lab.get_experiment('abc')
        self.assertEqual(cm.exception.code, 404)
        self.assertEqual(cm.exception.message, "Experiment 'abc' does not exist or does not belong to you.")

    def test_get_experiments(self):
        lab = make_lab()
        with patch_request(ok(experiments=[EXPERIMENT]), ok(experiments=[])) as request:
            self.assertEqual(lab.get_experiments(verbose=False), [EXPERIMENT])
            self.assertEqual(lab.get_experiments(verbose=False, fetch_max=50), [])
        first, second = request.call_args_list
        self.assertEqual((first.kwargs['url'], first.kwargs['params']), (ENDPOINT + '/experiments', {'limit': 10}))
        self.assertEqual(second.kwargs['params'], {'limit': 50})

    def test_get_experiments_prints_if_verbose(self):
        lab = make_lab()
        with patch_request(ok(experiments=[EXPERIMENT])), \
             mock.patch('causalchamber.lab.lab.print_experiments') as print_experiments:
            lab.get_experiments()
        print_experiments.assert_called_once_with([EXPERIMENT], 'user123', 10)

    def test_get_experiments_invalid_fetch_max(self):
        lab = make_lab()
        with patch_request() as request:
            for fetch_max, error in [(0, ValueError), (-1, ValueError), (None, TypeError), (2.5, TypeError)]:
                with self.subTest(fetch_max=fetch_max):
                    with self.assertRaises(error):
                        lab.get_experiments(fetch_max=fetch_max)
        request.assert_not_called()

    def test_cancel_experiment(self):
        lab = make_lab()
        canceled = dict(EXPERIMENT, status='CANCELED')
        with patch_request(ok(experiment=canceled)) as request:
            self.assertEqual(lab.cancel_experiment(EXPERIMENT['experiment_id']), canceled)
        call = request.call_args.kwargs
        self.assertEqual((call['method'], call['url'], call['json']),
                         ('POST', f"{ENDPOINT}/experiments/{EXPERIMENT['experiment_id']}/cancel", None))

    def test_cancel_experiment_not_found(self):
        lab = make_lab()
        with patch_request(response(404, NOT_FOUND)):
            with self.assertRaises(UserError) as cm:
                lab.cancel_experiment('abc')
        self.assertEqual(cm.exception.code, 404)

    def test_download_data_not_done(self):
        lab = make_lab()
        with patch_request(ok(experiment=EXPERIMENT)), \
             mock.patch('causalchamber.lab.lab.ExperimentDataset') as dataset:
            with self.assertRaises(UserError) as cm:
                lab.download_data(EXPERIMENT['experiment_id'], root='.')
        self.assertIn("is not finished yet (current status = QUEUED)", cm.exception.message)
        dataset.assert_not_called()

    def test_download_data_done(self):
        lab = make_lab()
        done = dict(EXPERIMENT, status='DONE', download_url='https://box.causalchamber.ai/results/x.zip',
                    checksum='sha256:a1b2')
        with patch_request(ok(experiment=done)), \
             mock.patch('causalchamber.lab.lab.ExperimentDataset') as dataset:
            lab.download_data(EXPERIMENT['experiment_id'], root='.', verbose=False)
        dataset.assert_called_once_with(experiment_id=EXPERIMENT['experiment_id'],
                                        download_url=done['download_url'], checksum=done['checksum'],
                                        root='.', verbose=False)


class ProtocolTests(unittest.TestCase):

    def setUp(self):
        self.protocol = make_lab().new_experiment('tt-test-virt', 'standard')
        self.protocol.wait(5000)
        self.protocol.set('var_2', 128)
        self.protocol.measure(10)

    def expected_body(self):
        return {'chamber_id': 'tt-test-virt', 'chamber_config': 'standard',
                'instructions': self.protocol.instructions}

    def test_new_experiment(self):
        self.assertIsInstance(self.protocol, Protocol)
        self.assertEqual((self.protocol.chamber_id, self.protocol.config), ('tt-test-virt', 'standard'))

    def test_submit(self):
        with patch_request(ok(experiment=EXPERIMENT), ok(experiment=EXPERIMENT)) as request:
            self.assertEqual(self.protocol.submit(), EXPERIMENT['experiment_id'])
            self.protocol.submit(tag='baseline_test')
        first, second = request.call_args_list
        self.assertEqual((first.kwargs['method'], first.kwargs['url'], first.kwargs['json']),
                         ('POST', ENDPOINT + '/experiments', self.expected_body()))
        self.assertEqual(second.kwargs['json'], dict(self.expected_body(), tag='baseline_test'))

    def test_submit_invalid_tag(self):
        with patch_request() as request:
            with self.assertRaises(TypeError):
                self.protocol.submit(tag=1)
        request.assert_not_called()

    def test_cost(self):
        quote = {'chamber_id': 'tt-test-virt', 'chamber_config': 'standard',
                 'credits_max': 2356, 'est_runtime_seconds': 2355.4}
        with patch_request(ok(quote=quote), ok(quote=quote)) as request:
            cost, output = captured_stdout(self.protocol.cost)
            self.assertEqual(captured_stdout(self.protocol.cost, verbose=False), (2356, ''))
        self.assertEqual(cost, 2356)
        self.assertEqual(output, "This experiment will cost at most 2,356 credits (estimated runtime is 40 min). "
                                 "If the experiment finishes before the estimated runtime, we will refund the difference.\n")
        call = request.call_args.kwargs
        self.assertEqual((call['method'], call['url'], call['json']),
                         ('POST', ENDPOINT + '/experiments/quote', self.expected_body()))


class SessionTests(unittest.TestCase):

    def setUp(self):
        self.lab = make_lab()

    def new_session(self, *outcomes):
        """Start a session, with the given responses to the requests after starting it."""
        patcher = patch_request(ok(session=STARTED_SESSION), *outcomes)
        self.request = patcher.start()
        self.addCleanup(patcher.stop)
        return self.lab.new_session('tt-test-virt', 'standard', duration=3600, verbose=False)

    def test_new_session(self):
        session = self.new_session()
        self.assertIsInstance(session, Session)
        self.assertIsInstance(session, Chamber)
        call = self.request.call_args.kwargs
        self.assertEqual((call['method'], call['url'], call['json']),
                         ('POST', ENDPOINT + '/sessions',
                          {'chamber_id': 'tt-test-virt', 'chamber_config': 'standard', 'duration_seconds': 3600}))
        self.assertEqual((session.session_id, session.chamber_id, session.config, session.model,
                          session.config_version, session.codebase_version, session.documentation),
                         (SESSION_ID, 'tt-test-virt', 'standard', 'Dummy Chamber Mk1', '1.0', '3f2a9c1', None))
        # The session uses the API client of the lab
        self.assertIs(session._API, self.lab._API)

    def test_instructions(self):
        session = self.new_session(response(200))
        self.assertIsNone(session.set('var_2', 128))
        call = self.request.call_args.kwargs
        self.assertEqual((call['method'], call['url'], call['json']),
                         ('POST', f'{ENDPOINT}/sessions/{SESSION_ID}/instructions',
                          {'instructions': ['SET,var_2,128.0']}))

    def test_wait(self):
        session = self.new_session(response(200), response(200))
        self.assertIsNone(session.wait(1000))
        self.assertEqual(self.request.call_args.kwargs['json'], {'instructions': ['WAIT,1000']})
        session.wait(30001, limit=None)
        self.assertEqual(self.request.call_args.kwargs['json'], {'instructions': ['WAIT,30001']})

    def test_wait_invalid_arguments(self):
        session = self.new_session()
        for milliseconds, error in [(30001, ValueError), (0, ValueError), (1.5, TypeError)]:
            with self.subTest(milliseconds=milliseconds):
                with self.assertRaises(error):
                    session.wait(milliseconds)
        with self.assertRaises(ValueError):
            session.wait(1001, limit=1000)
        # Only the request to start the session was made
        self.assertEqual(self.request.call_count, 1)

    def test_stop(self):
        session = self.new_session(ok(session=STOPPED_SESSION))
        self.assertEqual(session.stop(), STOPPED_SESSION)
        call = self.request.call_args.kwargs
        self.assertEqual((call['method'], call['url'], call['json']),
                         ('POST', f'{ENDPOINT}/sessions/{SESSION_ID}/stop', None))

    def test_context_manager_stops_session(self):
        with self.new_session(ok(session=STOPPED_SESSION)) as session:
            self.assertIsInstance(session, Session)
        self.assertEqual(self.request.call_count, 2)
        self.assertEqual(self.request.call_args.kwargs['url'], f'{ENDPOINT}/sessions/{SESSION_ID}/stop')

    def test_context_manager_ignores_inactive_session(self):
        # e.g., the session expired or was replaced during the block
        with self.new_session(response(409, NOT_ACTIVE)):
            pass
        self.assertEqual(self.request.call_count, 2)

    def test_context_manager_raises_stop_errors(self):
        with self.assertRaises(LabError):
            with self.new_session(response(500, {'message': 'Failed'})):
                pass

    def test_context_manager_keeps_exception_of_block(self):
        with self.assertRaises(RuntimeError):
            with self.new_session(ok(session=STOPPED_SESSION)):
                raise RuntimeError('error in the block')
        self.assertEqual(self.request.call_count, 2)
        # A failure to stop the session is only warned about
        with self.assertRaises(RuntimeError), self.assertWarns(UserWarning):
            with self.new_session(response(500, {'message': 'Failed'})):
                raise RuntimeError('error in the block')


class StopSessionTests(unittest.TestCase):

    def test_stop_session(self):
        lab = make_lab()
        with patch_request(ok(session=STOPPED_SESSION)) as request:
            session, output = captured_stdout(lab.stop_session, SESSION_ID)
        self.assertEqual(session, STOPPED_SESSION)
        self.assertEqual(output, f"Stopped session {SESSION_ID}; 3,000 credits were refunded for its unused time.\n")
        call = request.call_args.kwargs
        self.assertEqual((call['method'], call['url'], call['json']),
                         ('POST', f'{ENDPOINT}/sessions/{SESSION_ID}/stop', None))

    def test_stop_session_errors(self):
        lab = make_lab()
        with patch_request(response(404, NOT_FOUND), response(409, NOT_ACTIVE)):
            with self.assertRaises(UserError) as cm:
                lab.stop_session('abc', verbose=False)
            self.assertEqual(cm.exception.message, "Session 'abc' does not exist or does not belong to you.")
            with self.assertRaises(UserError) as cm:
                lab.stop_session(SESSION_ID, verbose=False)
            self.assertEqual((cm.exception.code, cm.exception.message), (409, NOT_ACTIVE['message']))
        with self.assertRaises(TypeError):
            lab.stop_session(1)


class StandaloneChamberTests(unittest.TestCase):

    def test_duration_is_optional(self):
        with patch_request(ok(session=STARTED_SESSION), ok(session=STARTED_SESSION)) as request:
            Chamber('tt-test-virt', 'standard', credentials=CREDENTIALS, endpoint=ENDPOINT, verbose=0)
            Chamber('tt-test-virt', 'standard', credentials=CREDENTIALS, endpoint=ENDPOINT, verbose=0, duration=600)
        first, second = request.call_args_list
        self.assertEqual(first.kwargs['json'], {'chamber_id': 'tt-test-virt', 'chamber_config': 'standard'})
        self.assertEqual(second.kwargs['json']['duration_seconds'], 600)


if __name__ == '__main__':
    unittest.main()
