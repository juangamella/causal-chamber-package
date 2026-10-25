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

"""Unit tests for causalchamber.lab.rendering: the views are rendered
as plain text and checked for their contents, and the live dashboard
(Lab.monitor) is run with mocked time, sleep and Jupyter output.
"""

# Packages from the standard library
import io
import sys
import types
import unittest
from unittest import mock

# Third party libraries
from rich.console import Console

# Imports from this package
from causalchamber.lab import rendering
from causalchamber.lab.chamber import Chamber
from causalchamber.lab.exceptions import LabError, UserError
from causalchamber.lab.test.mocks import patch_request
from causalchamber.lab.test.test_lab import (ACCOUNT, CHAMBER, CREDENTIALS, ENDPOINT, EXPERIMENT,
                                             SESSION, SESSION_ID, STARTED_SESSION, TRANSACTION, ok)

NOW = 1760000000.0
USER = 'user123'


def text(rendered):
    """Return a (renderable, width) pair as plain text."""
    return rendering.to_text(*rendered)


def experiment(**fields):
    return dict(EXPERIMENT, **fields)


def queue(n_queued, own_position=None):
    """Return a queue with an experiment in flight (another user's)
    and n_queued queued ones, the one at own_position being the user's."""
    experiments = [experiment(status='RUNNING', position=0, user_id=None, tag=None, experiment_id='in-flight',
                              started_on=NOW - 60, current_instruction=1)]
    for i in range(1, n_queued + 1):
        own = i == own_position
        experiments.append(experiment(position=i, experiment_id=f'queued-{i}',
                                      user_id=USER if own else None, tag='mine' if own else None))
    return experiments


class DashboardTests(unittest.TestCase):

    def render(self, account, **kwargs):
        return text(rendering._render(account, NOW, Console(width=200), **kwargs))

    def test_login_hint(self):
        output = self.render(ACCOUNT)
        self.assertIn(">>> account = rlab.dashboard() to print this dashboard   >>> rlab.monitor() to run it live", output)
        # The hint is above the footer, with a blank line in between
        lines = output.splitlines()
        footer = next(i for i, line in enumerate(lines) if 'Issues or feedback?' in line)
        self.assertIn('rlab.monitor()', lines[footer - 2])

    def test_live_dot_flickers(self):
        lit, unlit = rendering._monitor_hint(3), rendering._monitor_hint(3, lit=False)
        self.assertEqual(lit.plain, unlit.plain)
        self.assertNotEqual(lit.get_style_at_offset(Console(), 0), unlit.get_style_at_offset(Console(), 0))

    def test_custom_hint(self):
        output = self.render(ACCOUNT, hint=rendering._monitor_hint(3))
        self.assertIn("Press Ctrl+C to stop", output)
        self.assertNotIn("rlab.monitor()", output)

    def test_chambers_v1_fields(self):
        chambers = [{'chamber_id': 'lt-1', 'chamber_model': 'Light Tunnel Mk2', 'mode': 'queue',
                     'chamber_state': 'ready', 'available_on': None},
                    {'chamber_id': 'wt-2', 'chamber_model': 'Wind Tunnel Mk2', 'mode': None,
                     'chamber_state': 'unavailable', 'available_on': None}]
        output = self.render(dict(ACCOUNT, chambers=chambers))
        self.assertIn("1 / 2 ready", output)
        self.assertIn("Light Tunnel Mk2", output)
        self.assertIn("unavailable", output)
        self.assertIn("rlab.get_chamber('<chamber_id>')", output)
        # Unavailable chambers are listed last
        self.assertLess(output.index('lt-1'), output.index('wt-2'))

    def test_topup_hint(self):
        self.assertIn("rlab.topup()", self.render(ACCOUNT))

    def test_long_values_are_truncated(self):
        # Long values are cut, not the labels, and the panel keeps its width
        email = 'a.very.long.email.address@some-university.example.edu'
        output = self.render(dict(ACCOUNT, email=email))
        lines = [line[rendering._INDENT:rendering._INDENT + rendering._ACCOUNT_WIDTH] for line in output.splitlines()]
        email_line = next(line for line in lines if 'email' in line)
        self.assertIn('email       a.very.long', email_line)
        self.assertTrue(email_line.rstrip(' │').endswith('…'))
        self.assertTrue(any('user id     user123' in line for line in lines))

    def test_panel_titles(self):
        output = self.render(ACCOUNT)
        self.assertIn("Interactive Sessions", output)
        self.assertIn("Experiment Queue", output)

    def test_usage(self):
        def usage_lines(**fields):
            # The lines of the Account panel (the first after the indentation)
            output = self.render(dict(ACCOUNT, **fields))
            lines = [line[rendering._INDENT:rendering._INDENT + rendering._ACCOUNT_WIDTH].strip(' │')
                     for line in output.splitlines()]
            return [line for line in lines if 'usage' in line or 'pending' in line]
        self.assertEqual(usage_lines(requested_academic=True, is_academic=True), ['usage       academic'])
        self.assertEqual(usage_lines(requested_academic=False, is_academic=False), ['usage       commercial'])
        self.assertEqual(usage_lines(requested_academic=True, is_academic=False),
                         ['usage       academic', '(pending verification)'])


class ChamberViewTests(unittest.TestCase):

    def render(self, chamber, print_max=10):
        return text(rendering._render_chamber(chamber, USER, print_max, NOW))

    def test_info_and_configs(self):
        output = self.render(dict(CHAMBER, queue=[]))
        for expected in ["tt-test-virt", "Dummy Chamber Mk1", "● busy", "Variable Table",
                         "http://box.causalchamber.ai/config_doc_tt_mk1_standard.pdf",
                         "rlab.new_experiment('tt-test-virt', <config>)"]:
            self.assertIn(expected, output)

    def test_nothing_is_cropped(self):
        # The view is printed at the width it needs, so nothing is cut
        long_docs = 'http://box.causalchamber.ai/' + 'x' * 80 + '.pdf'
        chamber = dict(CHAMBER, queue=queue(3, own_position=2),
                       configs=[{'chamber_config': 'standard', 'config_version': '1.0', 'docs': long_docs}])
        output = self.render(chamber)
        self.assertIn(long_docs, output)
        self.assertNotIn('…', output)

    def test_queue(self):
        output = self.render(dict(CHAMBER, queue=queue(4, own_position=2)), print_max=2)
        self.assertIn("1 in flight · 4 waiting", output)
        self.assertIn("in-flight", output)
        self.assertIn("queued-1", output)
        self.assertIn("queued-2", output)
        self.assertNotIn("queued-3", output)
        self.assertIn("+ 2 more queued", output)
        # The user's own experiment is marked once, others' hidden fields are dashes
        own_line = next(line for line in output.splitlines() if 'queued-2' in line)
        self.assertEqual(own_line.count('yours'), 1)
        self.assertIn(f"{USER}  yours", own_line)
        other_line = next(line for line in output.splitlines() if 'queued-1' in line)
        self.assertIn("—", other_line)
        self.assertIn("rlab.cancel_experiment('<experiment_id>')", output)

    def test_submitting_is_waiting(self):
        # A submitting experiment is at position 0, but is shown with
        # the waiting ones, as in the dashboard
        submitting = experiment(status='SUBMITTING', position=0, experiment_id='submitting-0',
                                user_id=None, tag=None)
        output = self.render(dict(CHAMBER, queue=[submitting] + queue(2)[1:]))
        self.assertIn("0 in flight · 3 waiting", output)
        lines = output.splitlines()
        header = next(i for i, line in enumerate(lines) if 'Status' in line and '#' in line)
        self.assertIn('submitting-0', lines[header + 1])

    def test_queue_print_all(self):
        output = self.render(dict(CHAMBER, queue=queue(12)), print_max=None)
        self.assertIn("queued-12", output)
        self.assertNotIn("more queued", output)
        # No own experiments: no hint to cancel them
        self.assertNotIn("rlab.cancel_experiment", output)

    def test_empty_queue(self):
        self.assertIn("The queue is empty.", self.render(dict(CHAMBER, queue=[])))

    def interactive(self, session):
        return self.render(dict(CHAMBER, mode='interactive', queue=None, session=session))

    def test_own_session(self):
        output = self.interactive(dict(SESSION, expires_on=NOW + 600))
        self.assertIn(SESSION_ID, output)
        self.assertIn(f"{USER}  yours", output)
        self.assertIn("rlab.stop_session('<session_id>')", output)
        self.assertIn("rlab.new_session('tt-test-virt', <config>, <duration>)", output)

    def test_other_users_session(self):
        output = self.interactive(dict(SESSION, user_id=None, expires_on=NOW + 600))
        self.assertIn(SESSION_ID, output)
        self.assertNotIn("yours", output)
        self.assertNotIn("rlab.stop_session", output)

    def test_no_session(self):
        self.assertIn("No active session", self.interactive(None))

    def test_unavailable(self):
        output = self.render(dict(CHAMBER, mode=None, chamber_state='unavailable', available_on=None, queue=None))
        self.assertIn("not accepting experiments or sessions", output)
        self.assertNotIn("rlab.new_", output)


class ExperimentsViewTests(unittest.TestCase):

    def render(self, experiments, fetch_max=10):
        return text(rendering._render_experiments(experiments, USER, fetch_max, NOW))

    def test_three_panels(self):
        experiments = [experiment(status='DONE', experiment_id='done-1', current_instruction=3),
                       experiment(status='RUNNING', experiment_id='running-1', started_on=NOW - 10),
                       experiment(status='QUEUED', experiment_id='queued-1'),
                       experiment(status='SUBMITTING', experiment_id='submitting-1'),
                       experiment(status='FAILED', experiment_id='failed-1'),
                       experiment(status='CANCELED', experiment_id='canceled-1')]
        output = self.render(experiments)
        positions = [output.index(s) for s in ["In flight  1", "running-1", "Queued  2", "submitting-1",
                                               "queued-1", "Finished  3", "done-1", "failed-1", "canceled-1"]]
        self.assertEqual(positions, sorted(positions))
        for label in ["✓ done", "✗ failed", "⊘ canceled", "starting now", "rlab.download_data('<experiment_id>', '<root>')"]:
            self.assertIn(label, output)
        self.assertNotIn('…', output)

    def test_empty(self):
        output = self.render([])
        self.assertEqual(output.count("None."), 3)
        self.assertNotIn("rlab.", output)
        self.assertIn("You have not submitted any experiments yet.", output)

    def test_fetched_hint(self):
        experiments = [experiment(experiment_id=f'e-{i}') for i in range(3)]
        self.assertIn("Fetched all your 3 experiments.", self.render(experiments, fetch_max=10))
        output = self.render(experiments, fetch_max=3)
        self.assertIn("Fetched your 3 latest experiments.", output)
        self.assertIn("rlab.get_experiments(fetch_max=<n>) to fetch more", output)


class MonitorTests(unittest.TestCase):

    def test_fetches_every_refresh_rate(self):
        fetch = mock.Mock(return_value=ACCOUNT)
        # The fetches end at times 0 and 7
        with mock.patch.object(rendering.time, 'time', side_effect=[0, 7]):
            monitor = rendering._Monitor(fetch, 5)
            self.assertFalse(monitor.due(4.9))
            self.assertTrue(monitor.due(5))
            monitor.fetch()
        # The next fetch is counted from the end of the last one
        self.assertEqual((fetch.call_count, monitor.next_fetch), (2, 12))

    def test_keeps_last_account_on_lab_error(self):
        error = LabError(1, 'Could not connect to the API.')
        fetch = mock.Mock(side_effect=[ACCOUNT, error, dict(ACCOUNT, name='New')])
        with mock.patch.object(rendering.time, 'time', return_value=0):
            monitor = rendering._Monitor(fetch, 5)
            monitor.fetch()
            self.assertEqual((monitor.account, monitor.error), (ACCOUNT, error))
            output = text(monitor.render(1, Console(width=200)))
            self.assertIn("The last refresh failed", output)
            self.assertIn("Ada Lovelace", output)
            monitor.fetch()
        self.assertEqual((monitor.account['name'], monitor.error), ('New', None))

    def test_user_errors_propagate(self):
        monitor = rendering._Monitor(mock.Mock(side_effect=[ACCOUNT, UserError(401, 'Invalid credentials')]), 5)
        with self.assertRaises(UserError):
            monitor.fetch()

    def test_first_fetch_errors_propagate(self):
        with self.assertRaises(LabError):
            rendering._Monitor(mock.Mock(side_effect=LabError(1, 'Down')), 5)

    def test_terminal(self):
        # A terminal tall enough for the dashboard (see test_terminal_too_short)
        console = Console(file=io.StringIO(), width=200, height=60, force_terminal=True, color_system=None)
        times = iter([NOW, NOW + 1, NOW + 2, NOW + 3])
        with mock.patch.object(rendering.time, 'time', side_effect=lambda: next(times)), \
             mock.patch.object(rendering.time, 'sleep', side_effect=[None, KeyboardInterrupt]):
            monitor = rendering._Monitor(mock.Mock(return_value=ACCOUNT), 5)
            rendering._run_terminal(monitor, console)
        output = console.file.getvalue()
        self.assertIn("next refresh in 4s", output)
        self.assertIn("next refresh in 3s", output)
        # The dashboard left after stopping shows the login hint
        self.assertTrue(output.rstrip().endswith("support@causalchamber.ai and we'll be happy to help"))
        self.assertIn("rlab.monitor()", output[output.rindex("Account"):])

    def test_countdown_starts_after_fetch(self):
        # "refreshing…" is shown during a fetch, and the countdown
        # starts over from the full refresh rate once it ends, however
        # long it took (here, from NOW + 5 to NOW + 7)
        console = Console(file=io.StringIO(), width=200, height=60, force_terminal=True, color_system=None)
        times = iter([NOW, NOW + 5, NOW + 7, NOW + 7, NOW + 8])
        with mock.patch.object(rendering.time, 'time', side_effect=lambda: next(times)), \
             mock.patch.object(rendering.time, 'sleep', side_effect=KeyboardInterrupt):
            monitor = rendering._Monitor(mock.Mock(return_value=ACCOUNT), 5)
            rendering._run_terminal(monitor, console)
        output = console.file.getvalue()
        self.assertLess(output.index("refreshing…"), output.index("next refresh in 5s"))
        self.assertNotIn("next refresh in 3s", output)

    def test_terminal_too_short(self):
        # The live dashboard is cropped, but printed in full on exit
        console = Console(file=io.StringIO(), width=200, height=20, force_terminal=True, color_system=None)
        monitor = rendering._Monitor(mock.Mock(return_value=ACCOUNT), 5)
        with mock.patch.object(rendering.time, 'sleep', side_effect=KeyboardInterrupt):
            rendering._run_terminal(monitor, console)
        output = console.file.getvalue()
        self.assertNotIn("Press Ctrl+C to stop", output)
        self.assertIn("rlab.monitor() to run it live", output)
        self.assertTrue(output.rstrip().endswith("support@causalchamber.ai and we'll be happy to help"))

    def test_jupyter(self):
        display = types.ModuleType('IPython.display')
        display.clear_output = mock.Mock()
        console = mock.Mock(is_jupyter=True, width=115)
        printed = []
        with mock.patch.dict(sys.modules, {'IPython': types.ModuleType('IPython'), 'IPython.display': display}), \
             mock.patch.object(rendering.time, 'time', return_value=NOW + 1), \
             mock.patch.object(rendering.time, 'sleep', side_effect=[None, KeyboardInterrupt]), \
             mock.patch.object(rendering, '_print', side_effect=lambda r, w: printed.append(rendering.to_text(r, w))):
            monitor = rendering._Monitor(mock.Mock(return_value=ACCOUNT), 5)
            rendering._run_jupyter(monitor, console)
        self.assertEqual(display.clear_output.call_count, 3)
        display.clear_output.assert_called_with(wait=True)
        self.assertIn("Interrupt the kernel (■) to stop", printed[0])
        self.assertIn("rlab.monitor()", printed[-1])

    def test_run_monitor_chooses_mode(self):
        for jupyter in [False, True]:
            with self.subTest(jupyter=jupyter), \
                 mock.patch.object(rendering, 'Console', return_value=mock.Mock(is_jupyter=jupyter)), \
                 mock.patch.object(rendering, '_run_terminal') as run_terminal, \
                 mock.patch.object(rendering, '_run_jupyter') as run_jupyter:
                rendering.run_monitor(mock.Mock(return_value=ACCOUNT), 5)
            self.assertEqual((run_jupyter.called, run_terminal.called), (jupyter, not jupyter))


class TopupViewTests(unittest.TestCase):

    def test_payment_links(self):
        links = {'invoice': 'To pay via invoice or through a purchase order from your institution, '
                            'please write us at support@causalchamber.ai',
                 'card': 'https://pay.example.com/abc'}
        output = text(rendering._render_topup(links))
        self.assertIn("Top up your credits", output)
        self.assertIn("invoice", output)
        self.assertIn("https://pay.example.com/abc", output)
        # Long instructions wrap instead of being cut
        self.assertNotIn('…', output)
        self.assertIn("support@causalchamber.ai", output)

    def test_no_payment_links(self):
        self.assertIn("No ways to top up your credits", text(rendering._render_topup({})))

    def test_transactions_hint(self):
        self.assertIn(">>> rlab.get_transactions() to see your transactions",
                      text(rendering._render_topup({'card': 'https://pay.example.com/abc'})))


class TransactionsViewTests(unittest.TestCase):

    def render(self, transactions, fetch_max=10):
        return text(rendering._render_transactions(transactions, USER, fetch_max, NOW))

    def test_transactions(self):
        topup = dict(TRANSACTION, kind='topup', amount=3600, balance_after=3600, experiment_id=None, note=None)
        output = self.render([TRANSACTION, topup])
        for expected in ["Transactions", "charge", "-100", "3,500", "topup", "+3,600",
                         "rlab.topup() to top up your credits", "Fetched all your 2 transactions."]:
            self.assertIn(expected, output)
        # Long notes wrap instead of being cut
        self.assertNotIn('…', output)
        self.assertIn("(1 second = 1 credit).", output)
        self.assertLess(output.index('charge'), output.index('topup'))

    def test_fetched_hint(self):
        output = self.render([TRANSACTION] * 3, fetch_max=3)
        self.assertIn("Fetched your 3 latest transactions.", output)
        self.assertIn("rlab.get_transactions(fetch_max=<n>) to fetch more", output)

    def test_empty(self):
        output = self.render([])
        self.assertIn("Your wallet has no transactions yet.", output)
        self.assertNotIn("Fetched", output)


class SessionPanelTests(unittest.TestCase):

    def setUp(self):
        with patch_request(ok(session=STARTED_SESSION)):
            self.chamber = Chamber('tt-test-virt', 'standard', credentials=CREDENTIALS,
                                   endpoint=ENDPOINT, verbose=0, duration=600)

    def test_str_plain(self):
        with mock.patch('causalchamber.lab.chamber._is_interactive', return_value=False):
            output = str(self.chamber)
        self.assertNotIn('\x1b[', output)
        for expected in ["Causal Chamber® tt-test-virt", SESSION_ID, "Dummy Chamber Mk1", ENDPOINT, "3f2a9c1", "╭"]:
            self.assertIn(expected, output)

    def test_str_colored(self):
        with mock.patch('causalchamber.lab.chamber._is_interactive', return_value=True):
            self.assertIn('\x1b[', str(self.chamber))

    def test_rich(self):
        console = Console(file=io.StringIO(), width=200, color_system=None)
        console.print(self.chamber)
        self.assertIn(SESSION_ID, console.file.getvalue())


if __name__ == '__main__':
    unittest.main()
