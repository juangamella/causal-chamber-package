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

"""This module renders the output of the Remote Lab client with rich:

  - the dashboard, i.e., the panels with the user's account, the
    chambers, and the user's active sessions and experiments, from the
    account returned by GET /v1/account, printed once (on login) or
    live (Lab.monitor);
  - the details of a chamber (Lab.get_chamber), from GET
    /v1/chambers/{chamber_id};
  - the user's experiments (Lab.get_experiments), from GET
    /v1/experiments;
  - the ways to top up the credits (Lab.topup), from POST
    /v1/wallet/{wallet_id}/topup, and the transactions of the user's
    wallet (Lab.get_transactions), from GET /v1/transactions;
  - the panel of an interactive session (lab.Chamber, lab.Session).

All timestamps returned by the API are in seconds since the epoch
(UTC); they are shown in the local timezone of the machine.
"""

# Packages from the standard library
import io
import math
import time
from datetime import datetime

# Third-party packages
from rich import box
from rich.console import Console, Group
from rich.constrain import Constrain
from rich.live import Live
from rich.measure import Measurement
from rich.padding import Padding
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

# Imports from this package
from causalchamber import _PROMPT_STYLE, _CODE_STYLE
from causalchamber.lab.exceptions import LabError

# --------------------------------------------------------------------
# Layout and styles

# Indentation of the whole dashboard, in columns
_INDENT = 1
# Minimum width of the dashboard (without the indentation), in columns
_MIN_WIDTH = 116
# Width of the Account panel, and of the info panel of a chamber
_ACCOUNT_WIDTH = 38
_INFO_WIDTH = 52
# Columns between panels shown side by side (in a rich grid)
_GAP = 2
# Minimum number of lines inside the Account and Chambers panels,
# which are shown side by side and have the same height
_MIN_TOP_ROW_LINES = 10
# Maximum number of waiting (submitting or queued) experiments shown
_MAX_WAITING = 6
# Width of the progress bars (and of the countdown bar of the monitor)
_BAR_WIDTH = 13
# Seconds between redraws of the live dashboard (Lab.monitor), in a
# terminal and in Jupyter (where each redraw replaces the cell output)
_REDRAW_SECONDS = 0.25
_JUPYTER_REDRAW_SECONDS = 1

# Colors of the dashboard design (Claude Design hand-off), made for a
# dark background. Default text keeps the terminal's own color.
_DIM_STYLE = "#6c6f73"        # dim / secondary text
_MUTED_STYLE = "#9b9da0"      # muted labels and headers
_BORDER_STYLE = "#3b3e43"     # panel borders, dotted separator
_BAR_TRACK_STYLE = "#3b3e43"  # empty part of the progress bars
_GREEN = "#73c47f"            # ready, running, done, credits
_YELLOW = "#dcbc63"           # busy, queued
_CYAN = "#79bfe0"             # submitting, 'yours'
_ORANGE = "#e0956a"           # stopping, warnings
_RED = "#e06c6c"              # failed
_INK = "#121315"              # text of the badge in the header
_HEADER_STYLE = f"bold {_MUTED_STYLE}"

# Icon, label and style of each experiment status
_EXPERIMENT_STATUS = {
    'RUNNING': ('▶', 'running', _GREEN),
    'STOPPING': ('■', 'stopping', _ORANGE),
    'SUBMITTING': ('↑', 'submitting', _CYAN),
    'QUEUED': ('◦', 'queued', _YELLOW),
    'DONE': ('✓', 'done', _GREEN),
    'FAILED': ('✗', 'failed', _RED),
    'CANCELED': ('⊘', 'canceled', _DIM_STYLE),
}
_IN_FLIGHT = ('RUNNING', 'STOPPING')
_WAITING = ('SUBMITTING', 'QUEUED')
_FINISHED = ('DONE', 'FAILED', 'CANCELED')

# Style of each chamber state
_CHAMBER_STATE_STYLE = {'ready': _GREEN, 'busy': _YELLOW, 'unavailable': _DIM_STYLE}

# Columns of the experiment tables of the dashboard and of
# Lab.get_experiments (see _experiment_cells)
_EXPERIMENT_COLUMNS = ["Status", "Progress", "Runtime", "Experiment ID", "Tag", "Chamber", "Config", "Submitted"]
# Columns of the queue of a chamber (Lab.get_chamber)
_QUEUE_COLUMNS = ["#", "Status", "Progress", "Runtime", "Experiment ID", "User", "Tag", "Config", "Submitted"]

# Shown for missing values
_MISSING = "—"


# --------------------------------------------------------------------
# Public functions

def print_dashboard(account):
    """
    Print the dashboard for the given account.

    Parameters
    ----------
    account : dict
        The account, as returned by GET /v1/account.
    """
    _print(*_render(account, time.time(), Console()))


def run_monitor(fetch_account, refresh_rate):
    """
    Show the dashboard live, until it is interrupted (Ctrl+C in a
    terminal, interrupting the kernel in Jupyter). The account is
    fetched every refresh_rate seconds, and the countdown to the next
    refresh is animated in between.

    If a refresh fails because of an error on our side or a connection
    issue (LabError), the last dashboard is kept and the error is
    shown below it; the next refresh is tried as usual.

    Parameters
    ----------
    fetch_account : callable
        Function returning the account, as returned by GET /v1/account.
    refresh_rate : int or float
        Seconds between refreshes.

    Raises
    ------
    UserError or LabError
        If the first fetch of the account fails, or a later one
        raises a UserError (e.g., the credentials are no longer valid).
    """
    console = Console(highlight=False)
    monitor = _Monitor(fetch_account, refresh_rate)
    if console.is_jupyter:
        _run_jupyter(monitor, console)
    else:
        _run_terminal(monitor, console)


def print_chamber(chamber, user_id, print_max=10):
    """
    Print the details of a chamber: its info, its configurations,
    and its queue (in queue mode) or active session (in interactive
    mode).

    Parameters
    ----------
    chamber : dict
        The chamber, as returned by GET /v1/chambers/{chamber_id}.
    user_id : str
        The user's id, to tell the user's own experiments and session
        (shown with 'you' as their user) from those of other users
        (whose ids are dimmed).
    print_max : int or None, optional
        Maximum number of queued experiments to print. If None, all
        are printed. Default is 10.
    """
    _print(*_render_chamber(chamber, user_id, print_max, time.time()))


def print_experiments(experiments, user_id, fetch_max):
    """
    Print the given experiments in three panels: in flight, queued
    and finished, followed by how many were fetched.

    Parameters
    ----------
    experiments : list of dict
        The experiments, as returned by GET /v1/experiments.
    user_id : str
        The user's id, shown in the header.
    fetch_max : int
        The maximum number of experiments that was fetched (see
        Lab.get_experiments).
    """
    _print(*_render_experiments(experiments, user_id, fetch_max, time.time()))


def print_topup(payment_links):
    """
    Print the ways to top up the user's credits.

    Parameters
    ----------
    payment_links : dict
        The ways to top up the credits by name (payment links or
        instructions), as returned by POST /v1/wallet/{wallet_id}/topup.
    """
    _print(*_render_topup(payment_links))


def print_transactions(transactions, user_id, fetch_max):
    """
    Print the given transactions of the user's wallet, followed by
    how many were fetched.

    Parameters
    ----------
    transactions : list of dict
        The transactions, as returned by GET /v1/transactions.
    user_id : str
        The user's id, shown in the header.
    fetch_max : int
        The maximum number of transactions that was fetched (see
        Lab.get_transactions).
    """
    _print(*_render_transactions(transactions, user_id, fetch_max, time.time()))


def session_panel(chamber_id, fields):
    """
    Return the panel of an interactive session (see lab.Chamber), with
    a blank line before and after it, and the width (in columns) it
    should be printed at.

    Parameters
    ----------
    chamber_id : str
        The chamber's id, shown in the title.
    fields : list of (str, object)
        The label and value of each line; None values are shown as a
        dash.

    Returns
    -------
    (rich renderable, int)

    Examples
    --------
    >>> panel, width = session_panel('tt-test-virt', [('chamber_id', 'tt-test-virt'), ('documentation', None)])
    >>> print(to_text(panel, width), end='')
    <BLANKLINE>
     ╭─ Causal Chamber® tt-test-virt ─╮
     │ chamber_id     tt-test-virt    │
     │ documentation  —               │
     ╰────────────────────────────────╯
    <BLANKLINE>
    """
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style=_DIM_STYLE, no_wrap=True)
    grid.add_column(no_wrap=True)
    for label, value in fields:
        grid.add_row(label, _value(value))
    title = f"Causal Chamber® {chamber_id}"
    panel = _panel(grid, title)
    width = _panel_width(grid, title)
    return Padding(panel, (1, 0, 1, _INDENT)), width + _INDENT


def to_text(renderable, width, color=False):
    """
    Return the given renderable as text, rendered at the given width
    (in columns), with ANSI color codes if color=True.

    Examples
    --------
    >>> to_text(Text("ready", style=_GREEN), 10)
    'ready\\n'
    >>> to_text(Text("ready", style=_GREEN), 10, color=True)
    '\\x1b[38;2;115;196;127mready\\x1b[0m\\n'
    """
    console = Console(file=io.StringIO(), width=width, highlight=False, force_jupyter=False,
                      force_terminal=color, color_system="truecolor" if color else None)
    console.print(renderable)
    return console.file.getvalue()


# --------------------------------------------------------------------
# Rendering: common elements

def _print(renderable, width, file=None):
    """Print a renderable at the given width (in columns): if the
    terminal is narrower, its lines overflow (as with print()) instead
    of being cropped. It is printed to the given file, or to stdout if
    None."""
    Console(highlight=False, width=width, file=file).print(renderable)


class _TitleText(Text):
    """Text that ignores stylize_before, which rich.panel.Panel uses to
    give its title the style of the border."""

    def stylize_before(self, style, start=0, end=None):
        pass


class _Panel(Panel):
    """A rich panel whose title does not take the style (color) of its
    border, so that it has the default text color. Setting the title's
    color to 'default' does not work in Jupyter, where rich renders it
    black regardless of the notebook's theme."""

    @property
    def _title(self):
        title = super()._title
        if title is None:
            return None
        text = _TitleText(end=title.end, no_wrap=True)
        text.append_text(title)
        return text


def _panel(body, title, count=None, subtitle=None, height=None):
    """Return a dashboard panel with the given body, title, count
    (shown after the title) and subtitle (shown at the bottom)."""
    title_text = Text()
    title_text.append(title, style="bold")
    if count is not None:
        title_text.append(f"  {count}", style=_MUTED_STYLE)
    return _Panel(body, box=box.ROUNDED, border_style=_BORDER_STYLE,
                 title=title_text, title_align="left",
                 subtitle=subtitle, subtitle_align="right",
                 padding=(0, 1), height=height)


def _panel_width(body, title, count=None, subtitle=None):
    """Return the width (in columns) a panel needs to show the given
    body, title and subtitle without cropping them."""
    console = Console(width=10_000)
    content = Measurement.get(console, console.options, body).maximum
    title_width = len(title) + (len(count) + 2 if count is not None else 0)
    subtitle_width = subtitle.cell_len if subtitle is not None else 0
    # Borders and padding take 4 columns; the title and subtitle need
    # some space around them, and both fit on the borders
    return max(content + 4, title_width + 6, subtitle_width + 6)


def _table(headers, right_justified=(), widths=None, show_header=True):
    """Return a borderless table, with the given headers (styled as
    muted headers) and two spaces between columns. Cells do not wrap."""
    table = Table(box=None, show_header=show_header, header_style=_HEADER_STYLE,
                  padding=(0, 1), pad_edge=False, show_edge=False)
    for i, header in enumerate(headers):
        table.add_column(header, justify='right' if i in right_justified else 'left',
                         no_wrap=True, width=None if widths is None else widths[i])
    return table


def _column_widths(headers, rows):
    """Return the width of each column of a table with the given
    headers and rows (lists of rich Text), so that separate tables
    with the same columns can be aligned."""
    return [max(len(header), *(row[i].cell_len for row in rows)) for i, header in enumerate(headers)]


def _split_tables(headers, row_groups, right_justified=()):
    """Return the given groups of rows as separate tables with the same
    column widths, separated by dotted lines; only the first table
    has a header. Empty groups are skipped."""
    widths = _column_widths(headers, [row for rows in row_groups for row in rows])
    parts = []
    for rows in row_groups:
        if len(rows) == 0:
            continue
        if len(parts) > 0:
            parts.append(Rule(characters="┄", style=_BORDER_STYLE))
        table = _table(headers, right_justified, widths=widths, show_header=len(parts) == 0)
        for row in rows:
            table.add_row(*row)
        parts.append(table)
    return parts


def _prompt(code, note=None):
    """Return a line with the given code after the Python prompt,
    optionally followed by a (dimmed) note."""
    # Each part is styled separately (not through the base style of the
    # text), as rich drops the other styles of panel subtitles
    text = Text()
    text.append(">>> ", style=_PROMPT_STYLE)
    text.append(code, style=_CODE_STYLE)
    if note is not None:
        text.append(f" {note}", style=_DIM_STYLE)
    return text


def _header(user_id, now, view):
    """Return the header line (a badge with the view being shown, e.g.,
    'dashboard', the title, the user ID and the current local date
    and time) and the width it needs."""
    left = Text.assemble((f" {view} ", f"bold {_INK} on {_PROMPT_STYLE}"),
                         "  Causal Chamber® | ",
                         ("Remote Lab", "bold"),
                         (f"  {user_id or ''}", _DIM_STYLE))
    right = Text(_local(now).strftime('%a %b %d · %H:%M:%S %Z'), style=_DIM_STYLE)
    header = Table.grid(expand=True)
    header.add_column()
    header.add_column(justify='right')
    header.add_row(left, right)
    return header, left.cell_len + 2 + right.cell_len


def _footer():
    """Return the line shown below the panels, with the support email
    (a link, where supported)."""
    email = "support@causalchamber.ai"
    footer = Text("  Issues or feedback? Write us at ")
    footer.append(email, style=f"link mailto:{email}")
    footer.append(" and we'll be happy to help")
    return footer


def _theirs(text, own):
    """Return the given text (rich Text) dimmed if it belongs to
    another user (own is False), or as it is otherwise."""
    if own:
        return text
    text = text.copy()
    text.stylize(_DIM_STYLE)
    return text


def _user(user_id, own):
    """
    Return a user id as rich Text: 'you' (highlighted) if it is the
    user's own, the id otherwise (a dash if it is hidden).

    Examples
    --------
    >>> _user('user123', own=True).plain
    'you'
    >>> _user('user456', own=False).plain
    'user456'
    >>> _user(None, own=False).plain
    '—'
    """
    return Text("you", style=f"bold {_CYAN}") if own else _value(user_id)


# --------------------------------------------------------------------
# Rendering: dashboard

def _login_hint():
    """
    Return the hint shown below the dashboard printed on login (and
    by Lab.dashboard).

    Examples
    --------
    >>> _login_hint().plain
    '>>> account = rlab.dashboard() to print this dashboard   >>> rlab.monitor() to run it live'
    """
    return Text.assemble(_prompt("account = rlab.dashboard()", "to print this dashboard"), "   ",
                         _prompt("rlab.monitor()", "to run it live"))


def _render(account, now, console, hint=None, view='dashboard'):
    """
    Return the dashboard for the given account as a rich renderable,
    together with the width (in columns) it should be printed at.

    The whole dashboard is indented by one space, with a blank line
    before and after it. The Account and
    Chambers panels are shown side by side, unless the console is a
    terminal too narrow for that but wide enough for the dashboard
    with the two panels stacked. If the dashboard does not fit either
    way, it is wider than the terminal and its lines overflow.

    The hint (a rich renderable) is shown below the panels, above the
    footer: by default, how to run the dashboard live (see
    Lab.monitor). The view (e.g., 'monitor') is shown in the header.
    """
    sessions = account.get('sessions') or []
    chambers = account.get('chambers') or []
    # The Account and Chambers panels have the same height, enough to
    # fit the account details and all chambers (and their header)
    account_body, account_lines = _account_body(account)
    lines = max(_MIN_TOP_ROW_LINES, account_lines, len(chambers) + 1)
    account_panel = _panel(account_body, "Account", height=lines + 2)
    chambers_panel, chambers_width = _chambers_panel(chambers, sessions, now, lines)
    sessions_panel, sessions_width = _sessions_panel(sessions, now)
    experiments_panel, experiments_width = _experiments_panel(account.get('experiments') or [], now)
    header, header_width = _header(account.get('user_id'), now, view)
    wide_width = max(_MIN_WIDTH, _ACCOUNT_WIDTH + _GAP + chambers_width, sessions_width, experiments_width)
    stacked_width = max(header_width, _ACCOUNT_WIDTH, chambers_width, sessions_width, experiments_width)
    # Columns of the console available after the indentation
    available = console.width - _INDENT
    stacked = (not console.is_jupyter and available < wide_width
               and available >= stacked_width)
    if stacked:
        # The stacked dashboard fills the terminal
        width = available
        top = Group(account_panel, "", chambers_panel)
    else:
        width = wide_width
        top = Table.grid(padding=(0, 1), expand=True)
        top.add_column(width=_ACCOUNT_WIDTH)
        top.add_column(ratio=1)
        top.add_row(account_panel, chambers_panel)
    hint = Padding(_login_hint() if hint is None else hint, (0, 0, 0, 2))
    renderable = Group(header, "", top, "", sessions_panel, "", experiments_panel, "", hint, "", _footer())
    # Indent the dashboard, with a blank line before and after it
    return Padding(renderable, (1, 0, 1, _INDENT)), width + _INDENT


def _account_body(account):
    """Return the contents of the Account panel and its number of
    lines. Unless the credits are unlimited, it ends with how to top
    them up."""
    wallet = account.get('wallet') or {}
    rows = [("name", account.get('name')),
            ("user id", account.get('user_id')),
            ("email", account.get('email')),
            None,
            ("institution", account.get('institution')),
            ("usage", _fmt_usage(account))]
    # A requested academic status not verified yet is noted below
    if account.get('requested_academic') and not account.get('is_academic'):
        rows.append(("", Text("(pending verification)", style=_DIM_STYLE)))
    parts = [_account_grid(rows)]
    lines = len(rows)
    parts.append(_account_grid([None, ("credits", Text(_fmt_credits(wallet), style=_GREEN))]))
    lines += 2
    unlimited = 'credit_floor' in wallet and wallet['credit_floor'] is None
    if not unlimited:
        parts += ["", Text("Top up your credits with:", style=_DIM_STYLE), _prompt("rlab.topup()")]
        lines += 3
    return Group(*parts), lines


def _account_grid(rows):
    """Return a grid with the given rows of the Account panel: (label,
    value) pairs, or None for a blank line. Values that are not rich
    Text are formatted with _value."""
    # The values take the remaining width (ratio=1), and long ones are
    # truncated, instead of squeezing the labels
    grid = Table.grid(expand=True)
    grid.add_column(width=12, style=_DIM_STYLE, no_wrap=True)
    grid.add_column(no_wrap=True, overflow="ellipsis", ratio=1)
    for row in rows:
        if row is None:
            grid.add_row("", "")
        else:
            label, value = row
            grid.add_row(label, value if isinstance(value, Text) else _value(value))
    return grid


def _chambers_panel(chambers, sessions, now, lines):
    """Return the Chambers panel, with the given number of lines inside
    it, and the width it needs.

    The chambers are sorted with the ready ones first, then the busy
    ones by when they become available, then those held by the user's
    own sessions, then the unavailable ones.
    """
    own = {session.get('chamber_id') for session in sessions}
    n_ready = sum(chamber.get('chamber_state') == 'ready' for chamber in chambers)
    count = f"{n_ready} / {len(chambers)} ready"
    if len(chambers) == 0:
        body = Text("No chambers available.", style=_DIM_STYLE)
        return (_panel(body, "Chambers", count, height=lines + 2),
                _panel_width(body, "Chambers", count))
    subtitle = _prompt("rlab.get_chamber('<chamber_id>')", "for a chamber's details")

    def order(chamber):
        state = chamber.get('chamber_state')
        group = {'ready': 0, 'busy': 1}.get(state, 3)
        if state == 'busy' and chamber.get('chamber_id') in own:
            group = 2
        return (group, chamber.get('available_on') or 0, chamber.get('chamber_id') or '')

    table = _table(["", "Chamber", "Model", "", "Mode", "Available on"])
    for chamber in sorted(chambers, key=order):
        state = chamber.get('chamber_state')
        style = _CHAMBER_STATE_STYLE.get(state, _DIM_STYLE)
        table.add_row(Text("●", style=style),
                      _value(chamber.get('chamber_id')),
                      _value(chamber.get('chamber_model'), _MUTED_STYLE),
                      Text(state or _MISSING, style=style),
                      _value(chamber.get('mode'), _MUTED_STYLE),
                      _fmt_available(chamber, chamber.get('chamber_id') in own, now))
    return (_panel(table, "Chambers", count, subtitle, height=lines + 2),
            _panel_width(table, "Chambers", count, subtitle))


def _sessions_panel(sessions, now):
    """Return the Interactive Sessions panel and the width it needs."""
    count = f"{len(sessions)} active"
    if len(sessions) == 0:
        body = Text("You have no active sessions.", style=_DIM_STYLE)
        return _panel(body, "Interactive Sessions", count), _panel_width(body, "Interactive Sessions", count)
    table = _table(["", "Session ID", "Chamber", "Config", "Expires"])
    for session in sessions:
        table.add_row(Text("●", style=f"blink {_GREEN}"),
                      _value(session.get('session_id')),
                      _value(session.get('chamber_id')),
                      _value(session.get('chamber_config')),
                      _fmt_expires(session.get('expires_on'), now))
    subtitle = _prompt("rlab.stop_session('<session_id>')")
    return (_panel(table, "Interactive Sessions", count, subtitle),
            _panel_width(table, "Interactive Sessions", count, subtitle))


def _experiments_panel(experiments, now):
    """Return the Experiment Queue panel and the width it needs.

    The in-flight experiments (running or stopping) are shown first,
    followed by a dotted line and the waiting ones (submitting, then
    queued). At most _MAX_WAITING waiting experiments are shown; the
    rest are summarized as '+ N more queued'.
    """
    in_flight, waiting, _ = _by_status(experiments)
    count = f"{len(in_flight)} in flight · {len(waiting)} waiting"
    subtitle = _prompt("rlab.get_experiments()", "for history")
    if len(experiments) == 0:
        body = Text("You have no active experiments.", style=_DIM_STYLE)
        return (_panel(body, "Experiment Queue", count, subtitle),
                _panel_width(body, "Experiment Queue", count, subtitle))
    row_groups = [[_experiment_row(e, now, _EXPERIMENT_COLUMNS) for e in group]
                  for group in [in_flight, waiting[0:_MAX_WAITING]]]
    parts = _split_tables(_EXPERIMENT_COLUMNS, row_groups, right_justified=[2])
    if len(waiting) > _MAX_WAITING:
        parts.append(Text(f"+ {len(waiting) - _MAX_WAITING} more queued", style=_DIM_STYLE))
    body = Group(*parts)
    return (_panel(body, "Experiment Queue", count, subtitle),
            _panel_width(body, "Experiment Queue", count, subtitle))


# --------------------------------------------------------------------
# Rendering: live dashboard (Lab.monitor)

class _Monitor():
    """
    The state of the live dashboard: the last account fetched, when
    to fetch it next, and the error of the last fetch, if it failed.

    Parameters
    ----------
    fetch_account : callable
        Function returning the account.
    refresh_rate : int or float
        Seconds between fetches, counted from the end of the last
        fetch (so that the countdown does not include the time the
        request took). The account is fetched on initialization;
        errors are not caught then.
    """

    def __init__(self, fetch_account, refresh_rate):
        self._fetch_account = fetch_account
        self.refresh_rate = refresh_rate
        self.account = fetch_account()
        self.error = None
        self.next_fetch = time.time() + refresh_rate

    def due(self, now):
        """Return True if it is time to fetch the account."""
        return now >= self.next_fetch

    def fetch(self):
        """Fetch the account. If the fetch fails with a LabError, keep
        the last account and store the error."""
        try:
            self.account = self._fetch_account()
            self.error = None
        except LabError as e:
            self.error = e
        self.next_fetch = time.time() + self.refresh_rate

    def render(self, now, console, hint=None):
        """Return the dashboard and its width (see _render), by default
        live: with the countdown to the next refresh as its hint, and
        'monitor' in the header. With a hint (e.g., when the monitor
        stops), it is shown as the static dashboard."""
        if hint is not None:
            return _render(self.account, now, console, hint)
        # The live dot flickers: it is lit every other period (two
        # redraws in a terminal, one in Jupyter)
        period = _JUPYTER_REDRAW_SECONDS if console.is_jupyter else 2 * _REDRAW_SECONDS
        hint = _monitor_hint(self.next_fetch - now, self.error, console.is_jupyter,
                             lit=int(now / period) % 2 == 0)
        return _render(self.account, now, console, hint, view='monitor')


def _monitor_hint(remaining, error=None, jupyter=False, lit=True):
    """
    Return the hint shown below the live dashboard: a live dot (green
    if lit, dimmed otherwise, so that it flickers across redraws), the
    seconds left until the next refresh, how to stop the dashboard,
    and the error of the last refresh, if it failed.

    Examples
    --------
    >>> _monitor_hint(2.5).plain
    '● live  next refresh in 3s  ·  Press Ctrl+C to stop'
    >>> _monitor_hint(0, jupyter=True).plain
    '● live  refreshing…  ·  Interrupt the kernel (■) to stop'
    >>> print(_monitor_hint(4, error=LabError(1, 'Could not connect to the API.')).plain)
    ● live  next refresh in 4s  ·  Press Ctrl+C to stop
    ⚠ The last refresh failed; showing the data from before. (code 1) Could not connect to the API.
    """
    countdown = f"next refresh in {math.ceil(remaining)}s" if remaining > 0 else "refreshing…"
    stop = "Interrupt the kernel (■) to stop" if jupyter else "Press Ctrl+C to stop"
    hint = Text.assemble(("●", _GREEN if lit else _BAR_TRACK_STYLE), (" live", _GREEN),
                         (f"  {countdown}  ·  {stop}", _DIM_STYLE))
    if error is not None:
        hint.append(f"\n⚠ The last refresh failed; showing the data from before. (code {error.code}) {error.message}",
                    style=_ORANGE)
    return hint


def _run_terminal(monitor, console):
    """Run the live dashboard in a terminal, until Ctrl+C.

    The live dashboard is shown on the terminal's alternate screen (as
    full-screen programs do), so that it is redrawn cleanly even if it
    is taller than the terminal, in which case its bottom is cropped.
    On exit, the last dashboard is printed in full to the normal
    screen, with the hint shown on login."""
    try:
        with Live(console=console, auto_refresh=False, screen=True) as live:
            while True:
                now = time.time()
                if monitor.due(now):
                    # Show "refreshing…" while the account is fetched
                    live.update(Constrain(*monitor.render(now, console)), refresh=True)
                    monitor.fetch()
                    now = time.time()
                live.update(Constrain(*monitor.render(now, console)), refresh=True)
                time.sleep(_REDRAW_SECONDS)
    except KeyboardInterrupt:
        pass
    _print(*monitor.render(time.time(), console, _login_hint()), file=console.file)


def _run_jupyter(monitor, console):
    """Run the live dashboard in Jupyter, replacing the output of the
    cell on every redraw, until the kernel is interrupted. The last
    dashboard is left in the output, with the hint shown on login."""
    from IPython.display import clear_output
    try:
        while True:
            now = time.time()
            if monitor.due(now):
                # Show "refreshing…" while the account is fetched
                clear_output(wait=True)
                _print(*monitor.render(now, console))
                monitor.fetch()
                now = time.time()
            renderable, width = monitor.render(now, console)
            clear_output(wait=True)
            _print(renderable, width)
            time.sleep(_JUPYTER_REDRAW_SECONDS)
    except KeyboardInterrupt:
        clear_output(wait=True)
        _print(*monitor.render(time.time(), console, _login_hint()))


# --------------------------------------------------------------------
# Rendering: chamber details (Lab.get_chamber)

def _render_chamber(chamber, user_id, print_max, now):
    """
    Return the details of a chamber as a rich renderable, together
    with the width (in columns) it should be printed at.

    The chamber's info and configurations are shown side by side,
    followed by its queue (in queue mode), its active session (in
    interactive mode), or a note that it is unavailable (no mode).
    """
    configs = chamber.get('configs') or []
    session = chamber.get('session')
    own_session = session is not None and session.get('user_id') == user_id
    # The info and configurations panels have the same height
    info_body, info_lines = _chamber_info_body(chamber, own_session, now)
    lines = max(info_lines, len(configs) + 1)
    info_panel = _panel(info_body, "Chamber", height=lines + 2)
    configs_panel, configs_width = _configs_panel(chamber, lines)
    mode = chamber.get('mode')
    if mode == 'queue':
        bottom, bottom_width = _queue_panel(chamber.get('queue') or [], user_id, print_max, now)
    elif mode == 'interactive':
        bottom, bottom_width = _session_panel(session, own_session, now)
    else:
        body = Text("This chamber is not accepting experiments or sessions at the moment.", style=_DIM_STYLE)
        bottom, bottom_width = _panel(body, "Unavailable"), _panel_width(body, "Unavailable")
    header, header_width = _header(user_id, now, 'chamber')
    width = max(header_width, _INFO_WIDTH + _GAP + configs_width, bottom_width)
    top = Table.grid(padding=(0, 1), expand=True)
    top.add_column(width=_INFO_WIDTH)
    top.add_column(ratio=1)
    top.add_row(info_panel, configs_panel)
    renderable = Group(header, "", top, "", bottom)
    return Padding(renderable, (1, 0, 1, _INDENT)), width + _INDENT


def _chamber_info_body(chamber, own_session, now):
    """Return the contents of the chamber's info panel and its number
    of lines."""
    state = chamber.get('chamber_state')
    # As in _account_grid, long values are truncated, not the labels
    grid = Table.grid(expand=True)
    grid.add_column(width=12, style=_DIM_STYLE, no_wrap=True)
    grid.add_column(no_wrap=True, overflow="ellipsis", ratio=1)
    grid.add_row("chamber id", _value(chamber.get('chamber_id')))
    grid.add_row("model", _value(chamber.get('chamber_model')))
    grid.add_row("mode", _value(chamber.get('mode')))
    grid.add_row("state", Text.assemble(("● ", _CHAMBER_STATE_STYLE.get(state, _DIM_STYLE)),
                                        (state or _MISSING, _CHAMBER_STATE_STYLE.get(state, _DIM_STYLE))))
    grid.add_row("available", _fmt_available(chamber, own_session, now))
    return grid, 5


def _configs_panel(chamber, lines):
    """Return the panel with the chamber's configurations (with the
    links to their variable tables), with the given number of lines
    inside it, and the width it needs. Its subtitle shows how to use
    the chamber in its current mode."""
    configs = chamber.get('configs') or []
    chamber_id = chamber.get('chamber_id')
    subtitle = {'queue': _prompt(f"rlab.new_experiment('{chamber_id}', <config>)"),
                'interactive': _prompt(f"rlab.new_session('{chamber_id}', <config>, <duration>)")
                }.get(chamber.get('mode'))
    count = str(len(configs))
    if len(configs) == 0:
        body = Text("No configurations.", style=_DIM_STYLE)
    else:
        body = _table(["Config", "Version", "Variable Table"])
        for config in configs:
            docs = config.get('docs')
            body.add_row(_value(config.get('chamber_config')),
                         _value(config.get('config_version'), _MUTED_STYLE),
                         _value(docs) if docs is None else Text(docs, style=f"link {docs}"))
    return (_panel(body, "Configurations", count, subtitle, height=lines + 2),
            _panel_width(body, "Configurations", count, subtitle))


def _queue_panel(queue, user_id, print_max, now):
    """Return the Experiment Queue panel and the width it needs.

    As in the dashboard, the experiment in flight (running or
    stopping), if any, is shown first, followed by a dotted line and
    the waiting experiments (submitting, then queued) in order: at
    most print_max of them (all if None); the rest are summarized as
    '+ N more queued'. Other users' ids and tags may be hidden (None),
    and are shown as a dash; the ids of other users' experiments are
    dimmed, and the user's own show 'you' as their user.
    """
    queue = sorted(queue, key=lambda e: e.get('position') or 0)
    # A submitting experiment is at position 0, but has not started
    in_flight, queued, _ = _by_status(queue)
    shown = queued if print_max is None else queued[0:print_max]
    count = f"{len(in_flight)} in flight · {len(queued)} waiting"
    if len(queue) == 0:
        body = Text("The queue is empty.", style=_DIM_STYLE)
        return _panel(body, "Experiment Queue", count), _panel_width(body, "Experiment Queue", count)
    own = any(e.get('user_id') == user_id for e in queued)
    subtitle = _prompt("rlab.cancel_experiment('<experiment_id>')") if own else None
    row_groups = [[_queue_row(e, user_id, now) for e in group] for group in [in_flight, shown]]
    parts = _split_tables(_QUEUE_COLUMNS, row_groups, right_justified=[0, 3])
    if len(queued) > len(shown):
        parts.append(Text(f"+ {len(queued) - len(shown)} more queued", style=_DIM_STYLE))
    body = Group(*parts)
    return (_panel(body, "Experiment Queue", count, subtitle),
            _panel_width(body, "Experiment Queue", count, subtitle))


def _queue_row(experiment, user_id, now):
    """Return the cells of the row of the given experiment in the queue
    of a chamber."""
    own = experiment.get('user_id') == user_id
    cells = _experiment_cells(experiment, now)
    cells["#"] = _value(experiment.get('position'), _MUTED_STYLE)
    cells["Experiment ID"] = _theirs(cells["Experiment ID"], own)
    cells["User"] = _user(experiment.get('user_id'), own)
    return [cells[column] for column in _QUEUE_COLUMNS]


def _session_panel(session, own, now):
    """Return the Interactive Session panel (the active session of a chamber in
    interactive mode) and the width it needs."""
    if session is None:
        body = Text("No active session: the chamber is free.", style=_DIM_STYLE)
        return _panel(body, "Interactive Session"), _panel_width(body, "Interactive Session")
    table = _table(["", "Session ID", "User", "Config", "Started", "Expires"])
    started_on = session.get('started_on')
    table.add_row(Text("●", style=f"blink {_GREEN}"),
                  _theirs(_value(session.get('session_id')), own),
                  _user(session.get('user_id'), own),
                  _value(session.get('chamber_config')),
                  Text(_MISSING if started_on is None else _fmt_submitted(started_on, now), style=_DIM_STYLE),
                  _fmt_expires(session.get('expires_on'), now))
    subtitle = _prompt("rlab.stop_session('<session_id>')") if own else None
    return (_panel(table, "Interactive Session", subtitle=subtitle),
            _panel_width(table, "Interactive Session", subtitle=subtitle))


# --------------------------------------------------------------------
# Rendering: top up (Lab.topup)

def _render_topup(payment_links):
    """
    Return the ways to top up the credits as a rich renderable (a
    panel, with a blank line before and after it), together with the
    width (in columns) it should be printed at: the width the panel
    needs, at most _MIN_WIDTH, beyond which long values wrap.
    """
    # The names do not wrap; long values (e.g., instructions) do, if
    # the panel is capped at _MIN_WIDTH
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style=_DIM_STYLE, no_wrap=True)
    grid.add_column()
    for name, value in payment_links.items():
        grid.add_row(name, _payment_link(value))
    title = "Top up your credits"
    if len(payment_links) == 0:
        body = Text("No ways to top up your credits are available. Please write us at support@causalchamber.ai.",
                    style=_DIM_STYLE)
    else:
        body = grid
    subtitle = _prompt("rlab.get_transactions()", "to see your transactions")
    width = min(_panel_width(body, title, subtitle=subtitle), _MIN_WIDTH)
    return Padding(_panel(body, title, subtitle=subtitle), (1, 0, 1, _INDENT)), width + _INDENT


def _payment_link(value):
    """
    Return a way to top up the credits as rich Text: a link if it is
    a URL, the text as it is otherwise (e.g., instructions).

    Examples
    --------
    >>> _payment_link('https://pay.example.com/abc').style
    'link https://pay.example.com/abc'
    >>> text = _payment_link('Please write us at support@causalchamber.ai')
    >>> text.plain, text.style
    ('Please write us at support@causalchamber.ai', '')
    >>> _payment_link(None).plain
    '—'
    """
    if isinstance(value, str) and value.startswith(('https://', 'http://')):
        return Text(value, style=f"link {value}")
    return _value(value)


# --------------------------------------------------------------------
# Rendering: transactions (Lab.get_transactions)

def _render_transactions(transactions, user_id, fetch_max, now):
    """
    Return the given transactions as a rich renderable, together with
    the width (in columns) it should be printed at: a panel with one
    row per transaction, newest first, followed by how many were
    fetched (see _fetched_hint). The panel is at most _MIN_WIDTH
    wide, beyond which the notes wrap.
    """
    title = "Transactions"
    subtitle = _prompt("rlab.topup()", "to top up your credits")
    if len(transactions) == 0:
        body = Text("Your wallet has no transactions yet.", style=_DIM_STYLE)
    else:
        body = _table(["Date", "Kind", "Amount", "Balance", "Note"], right_justified=[2, 3])
        # Only the notes wrap, as they can be long
        body.columns[-1].no_wrap = False
        for transaction in transactions:
            body.add_row(*_transaction_row(transaction))
    header, header_width = _header(user_id, now, 'transactions')
    width = max(header_width, min(_panel_width(body, title, subtitle=subtitle), _MIN_WIDTH))
    parts = [header, "", _panel(body, title, subtitle=subtitle)]
    if len(transactions) > 0:
        parts += ["", Padding(_fetched_hint(len(transactions), fetch_max, noun='transaction'), (0, 0, 0, 2))]
    return Padding(Group(*parts), (1, 0, 1, _INDENT)), width + _INDENT


def _transaction_row(transaction):
    """
    Return the cells (rich Text) of the row of the given transaction:
    its date, kind, amount (signed, green if credits were added),
    balance after it and note.

    Examples
    --------
    >>> row = _transaction_row({'kind': 'charge', 'amount': -1200, 'balance_after': 3500,
    ...                         'note': None, 'created_on': None})
    >>> [cell.plain for cell in row]
    ['—', 'charge', '-1,200', '3,500', '—']
    >>> _transaction_row({'kind': 'topup', 'amount': 5000})[2].plain
    '+5,000'
    """
    amount = transaction.get('amount')
    if amount is None:
        amount_cell = _value(None)
    else:
        amount_cell = Text(f"{amount:+,}", style=_GREEN if amount > 0 else "")
    balance = transaction.get('balance_after')
    created_on = transaction.get('created_on')
    return [_value(None if created_on is None else _local(created_on).strftime('%Y-%m-%d %H:%M')),
            _value(transaction.get('kind')),
            amount_cell,
            _value(None if balance is None else f"{balance:,}"),
            _value(transaction.get('note'), style=_MUTED_STYLE)]


# --------------------------------------------------------------------
# Rendering: experiments (Lab.get_experiments)

def _render_experiments(experiments, user_id, fetch_max, now):
    """
    Return the given experiments as a rich renderable, together with
    the width (in columns) it should be printed at: three panels with
    the experiments in flight (running or stopping), waiting
    (submitting, then queued) and finished (done, failed or canceled),
    newest first, with aligned columns, followed by how many were
    fetched (see _fetched_hint).
    """
    groups = _by_status(experiments)
    row_groups = [[_experiment_row(e, now, _EXPERIMENT_COLUMNS) for e in group] for group in groups]
    all_rows = [row for rows in row_groups for row in rows]
    widths = _column_widths(_EXPERIMENT_COLUMNS, all_rows) if all_rows else None
    titles = ["In flight", "Queued", "Finished"]
    subtitles = [_prompt("rlab.cancel_experiment('<experiment_id>')"),
                 _prompt("rlab.cancel_experiment('<experiment_id>')"),
                 _prompt("rlab.download_data('<experiment_id>', '<root>')")]
    panels, widths_needed = [], []
    for title, subtitle, rows in zip(titles, subtitles, row_groups):
        if len(rows) == 0:
            body, subtitle = Text("None.", style=_DIM_STYLE), None
        else:
            body = _table(_EXPERIMENT_COLUMNS, right_justified=[2], widths=widths)
            for row in rows:
                body.add_row(*row)
        panels.append(_panel(body, title, str(len(rows)), subtitle))
        widths_needed.append(_panel_width(body, title, str(len(rows)), subtitle))
    header, header_width = _header(user_id, now, 'experiments')
    width = max(header_width, *widths_needed)
    hint = Padding(_fetched_hint(len(experiments), fetch_max), (0, 0, 0, 2))
    renderable = Group(header, "", panels[0], "", panels[1], "", panels[2], "", hint)
    return Padding(renderable, (1, 0, 1, _INDENT)), width + _INDENT


def _fetched_hint(n, fetch_max, noun='experiment'):
    """
    Return the hint below the experiments printed by
    Lab.get_experiments (or the transactions printed by
    Lab.get_transactions, with noun='transaction'): how many were
    fetched and, if there may be more (n = fetch_max), how to fetch
    them.

    Examples
    --------
    >>> _fetched_hint(10, 10).plain
    'Fetched your 10 latest experiments.   >>> rlab.get_experiments(fetch_max=<n>) to fetch more'
    >>> _fetched_hint(1, 1).plain
    'Fetched your latest experiment.   >>> rlab.get_experiments(fetch_max=<n>) to fetch more'
    >>> _fetched_hint(3, 10).plain
    'Fetched all your 3 experiments.'
    >>> _fetched_hint(0, 10).plain
    'You have not submitted any experiments yet.'
    >>> _fetched_hint(5, 5, noun='transaction').plain
    'Fetched your 5 latest transactions.   >>> rlab.get_transactions(fetch_max=<n>) to fetch more'
    """
    if n == 0:
        return Text("You have not submitted any experiments yet.", style=_DIM_STYLE)
    elif n < fetch_max:
        return Text(f"Fetched all your {n} {noun}{'s' if n > 1 else ''}.", style=_DIM_STYLE)
    latest = f"your latest {noun}" if n == 1 else f"your {n} latest {noun}s"
    return Text.assemble((f"Fetched {latest}.   ", _DIM_STYLE),
                         _prompt(f"rlab.get_{noun}s(fetch_max=<n>)", "to fetch more"))


# --------------------------------------------------------------------
# Rendering: experiments

def _by_status(experiments):
    """
    Split the given experiments into those in flight (running or
    stopping), waiting (submitting, then queued) and finished (done,
    failed or canceled), keeping their order otherwise.

    Examples
    --------
    >>> experiments = [{'status': s} for s in ['QUEUED', 'DONE', 'RUNNING', 'SUBMITTING', 'CANCELED']]
    >>> [[e['status'] for e in group] for group in _by_status(experiments)]
    [['RUNNING'], ['SUBMITTING', 'QUEUED'], ['DONE', 'CANCELED']]
    """
    in_flight = [e for e in experiments if e.get('status') in _IN_FLIGHT]
    waiting = ([e for e in experiments if e.get('status') == 'SUBMITTING'] +
               [e for e in experiments if e.get('status') not in _IN_FLIGHT + _FINISHED + ('SUBMITTING',)])
    finished = [e for e in experiments if e.get('status') in _FINISHED]
    return in_flight, waiting, finished


def _experiment_row(experiment, now, columns):
    """Return the cells (rich Text) of the row of the given experiment,
    for the given columns (see _experiment_cells)."""
    cells = _experiment_cells(experiment, now)
    return [cells[column] for column in columns]


def _experiment_cells(experiment, now):
    """
    Return the cells (rich Text) describing the given experiment, by
    column: Status, Progress, Runtime, Experiment ID, Tag, Chamber,
    Config and Submitted.

    Examples
    --------
    >>> experiment = {'status': 'FAILED', 'current_instruction': 50, 'total_instructions': 100,
    ...               'started_on': None, 'est_runtime_seconds': 120, 'experiment_id': 'f47ac10b',
    ...               'tag': '', 'chamber_id': 'lt-1', 'chamber_config': 'standard', 'submitted_on': None}
    >>> {column: cell.plain for column, cell in _experiment_cells(experiment, now=0).items()}
    {'Status': '✗ failed', 'Progress': '━━━━━━━━━━━━━  50%', 'Runtime': '02:00', 'Experiment ID': 'f47ac10b', 'Tag': '', 'Chamber': 'lt-1', 'Config': 'standard', 'Submitted': '—'}
    """
    status = experiment.get('status')
    icon, label, style = _EXPERIMENT_STATUS.get(status, ("•", str(status).lower(), ""))
    if status in _IN_FLIGHT + _FINISHED:
        progress = _progress_bar(experiment, style)
    elif status == 'SUBMITTING':
        progress = Text("starting now", style=_CYAN)
    else:
        progress = Text("")
    submitted_on = experiment.get('submitted_on')
    # The icon of active experiments blinks (in terminals that support it)
    icon_style = style if status in _FINISHED else f"blink {style}"
    return {"Status": Text.assemble((icon, icon_style), (f" {label}", style)),
            "Progress": progress,
            "Runtime": _fmt_runtime(experiment, now),
            "Experiment ID": _value(experiment.get('experiment_id')),
            "Tag": _value(experiment.get('tag'), _MUTED_STYLE),
            "Chamber": _value(experiment.get('chamber_id')),
            "Config": _value(experiment.get('chamber_config'), _MUTED_STYLE),
            "Submitted": Text(_MISSING if submitted_on is None else _fmt_submitted(submitted_on, now), style=_DIM_STYLE)}


def _progress_bar(experiment, style):
    """
    Return a progress bar with the percentage of instructions executed
    by the experiment.

    Examples
    --------
    >>> _progress_bar({'current_instruction': 72, 'total_instructions': 100}, 'green').plain
    '━━━━━━━━━━━━━  72%'
    >>> _progress_bar({'current_instruction': None, 'total_instructions': 100}, 'green').plain
    '━━━━━━━━━━━━━   0%'
    """
    total = experiment.get('total_instructions')
    current = experiment.get('current_instruction') or 0
    percent = min(100, max(0, math.floor(current / total * 100))) if total else 0
    filled = round(percent / 100 * _BAR_WIDTH)
    return Text.assemble(("━" * filled, style),
                         ("━" * (_BAR_WIDTH - filled), _BAR_TRACK_STYLE),
                         f" {percent:>3}%")


# --------------------------------------------------------------------
# Formatting of values

def _value(value, style=""):
    """Return the given value as plain text (not parsed as rich
    markup) with the given style, or a dimmed dash if it is None."""
    if value is None:
        return Text(_MISSING, style=_DIM_STYLE)
    return Text(str(value), style=style)


def _local(timestamp):
    """Return the given timestamp (seconds since the epoch) as an aware
    datetime in the local timezone of the machine."""
    return datetime.fromtimestamp(timestamp).astimezone()


def _fmt_usage(account):
    """
    Return the usage of an account: academic if its academic status
    has been verified or requested (pending verification), commercial
    otherwise.

    Examples
    --------
    >>> _fmt_usage({'requested_academic': True, 'is_academic': True})
    'academic'
    >>> _fmt_usage({'requested_academic': True, 'is_academic': False})
    'academic'
    >>> _fmt_usage({'requested_academic': False, 'is_academic': False})
    'commercial'
    >>> _fmt_usage({}) is None
    True
    """
    if account.get('is_academic') is None:
        return None
    academic = account['is_academic'] or account.get('requested_academic')
    return 'academic' if academic else 'commercial'


def _fmt_credits(wallet):
    """
    Return the credits available in a wallet: its credits minus its
    credit floor, or '∞ unlimited' if it has no credit floor.

    Examples
    --------
    >>> _fmt_credits({'credits': 3600, 'credit_floor': 0})
    '3,600'
    >>> _fmt_credits({'credits': 100, 'credit_floor': -500})
    '600'
    >>> _fmt_credits({'credits': 3600, 'credit_floor': None})
    '∞ unlimited'
    >>> _fmt_credits({})
    '—'
    """
    if wallet.get('credits') is None or 'credit_floor' not in wallet:
        return _MISSING
    elif wallet['credit_floor'] is None:
        return '∞ unlimited'
    else:
        return f"{wallet['credits'] - wallet['credit_floor']:,}"


def _fmt_duration(seconds):
    """
    Return a duration in seconds as a short, human-readable string,
    rounded up to the minute.

    Examples
    --------
    >>> _fmt_duration(10)
    '1 min'
    >>> _fmt_duration(9 * 60)
    '9 min'
    >>> _fmt_duration(3 * 3600 + 5 * 60)
    '3h 5m'
    >>> _fmt_duration(29 * 86400 + 22 * 3600)
    '29d 22h'
    """
    minutes = max(1, math.ceil(seconds / 60))
    if minutes < 60:
        return f"{minutes} min"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h {minutes}m"
    days, hours = divmod(hours, 24)
    return f"{days}d {hours}h"


def _fmt_seconds(seconds):
    """
    Return a duration in seconds as hours, minutes and seconds,
    rounded up to the second and leaving out the parts that are zero.

    Examples
    --------
    >>> _fmt_seconds(104)
    '1m 44s'
    >>> _fmt_seconds(44.2)
    '45s'
    >>> _fmt_seconds(120)
    '2m'
    >>> _fmt_seconds(3 * 3600 + 5)
    '3h 5s'
    >>> _fmt_seconds(0)
    '0s'
    """
    hours, rest = divmod(math.ceil(max(0, seconds)), 3600)
    minutes, seconds = divmod(rest, 60)
    parts = [f"{value}{unit}" for value, unit in [(hours, 'h'), (minutes, 'm'), (seconds, 's')] if value > 0]
    return " ".join(parts) if parts else "0s"


def _fmt_clock(seconds):
    """
    Return a duration in seconds as mm:ss, or h:mm:ss if it is an hour
    or longer.

    Examples
    --------
    >>> _fmt_clock(252)
    '04:12'
    >>> _fmt_clock(3 * 3600 + 61)
    '3:01:01'
    >>> _fmt_clock(-5)
    '00:00'
    """
    hours, rest = divmod(round(max(0, seconds)), 3600)
    minutes, seconds = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours > 0 else f"{minutes:02d}:{seconds:02d}"


def _fmt_runtime(experiment, now):
    """
    Return the runtime of an experiment: the elapsed time over its
    estimated runtime if it is in flight, or only its estimated
    runtime otherwise.

    Examples
    --------
    >>> _fmt_runtime({'status': 'RUNNING', 'started_on': 1000, 'est_runtime_seconds': 600}, now=1252).plain
    '04:12 / 10:00'
    >>> _fmt_runtime({'status': 'QUEUED', 'started_on': None, 'est_runtime_seconds': 600}, now=1252).plain
    '10:00'
    """
    estimate = experiment.get('est_runtime_seconds')
    started_on = experiment.get('started_on')
    if experiment.get('status') in _IN_FLIGHT and started_on is not None:
        text = Text(_fmt_clock(now - started_on))
        if estimate is not None:
            text.append(f" / {_fmt_clock(estimate)}", style=_DIM_STYLE)
        return text
    return Text(_MISSING if estimate is None else _fmt_clock(estimate), style=_MUTED_STYLE)


def _fmt_available(chamber, own, now):
    """
    Return when a chamber becomes available: 'now' if it is ready, or,
    if it is busy, the local date and time followed by the (dimmed)
    time until then. In queue mode, these are an estimate, marked with
    '~'. Chambers held by one of the user's sessions are marked as
    'yours'.

    Examples
    --------
    >>> _fmt_available({'chamber_state': 'ready'}, own=False, now=0).plain
    'now'
    >>> _fmt_available({'chamber_state': 'busy', 'mode': 'queue', 'available_on': 540}, own=False, now=0).plain
    '...  in ~9 min'
    >>> _fmt_available({'chamber_state': 'busy', 'mode': 'interactive', 'available_on': 2584800}, own=True, now=0).plain
    '...  in 29d 22h  yours'
    >>> _fmt_available({'chamber_state': 'unavailable', 'available_on': None}, own=False, now=0).plain
    '—'
    """
    state = chamber.get('chamber_state')
    available_on = chamber.get('available_on')
    if state == 'ready':
        return Text("now", style=f"bold {_GREEN}")
    elif state != 'busy' or available_on is None:
        text = Text(_MISSING, style=_DIM_STYLE)
    elif available_on <= now:
        text = Text("soon")
    else:
        estimate = "~" if chamber.get('mode') == 'queue' else ""
        text = Text.assemble(_local(available_on).strftime('%a %b %d %H:%M'),
                             (f"  in {estimate}{_fmt_duration(available_on - now)}", _DIM_STYLE))
    if own:
        text.append("  yours", style=_CYAN)
    return text


def _fmt_expires(expires_on, now):
    """
    Return when a session expires: the time until then, followed by
    the (dimmed) local date and time.
    """
    if expires_on is None:
        return Text(_MISSING, style=_DIM_STYLE)
    relative = f"in {_fmt_duration(expires_on - now)}" if expires_on > now else "expired"
    return Text.assemble(relative, (f"  {_local(expires_on).strftime('%a %b %d %H:%M')}", _DIM_STYLE))


def _fmt_submitted(timestamp, now):
    """
    Return a timestamp in at most 12 characters, with more detail the
    more recent it is: the time if it is today, the weekday and time
    if it is within the last 6 days, the date and time if it is this
    year, and the date otherwise.

    Examples
    --------
    >>> now = datetime(2026, 10, 16, 21, 47, 46).timestamp()
    >>> _fmt_submitted(datetime(2026, 10, 16, 21, 47, 26).timestamp(), now)
    '21:47:26'
    >>> _fmt_submitted(datetime(2026, 10, 15, 18, 2).timestamp(), now)
    'Thu 18:02'
    >>> _fmt_submitted(datetime(2026, 3, 12, 9, 15).timestamp(), now)
    'Mar 12 09:15'
    >>> _fmt_submitted(datetime(2025, 10, 12, 9, 15).timestamp(), now)
    '2025-10-12'
    """
    submitted, today = _local(timestamp), _local(now)
    days_ago = (today.date() - submitted.date()).days
    if days_ago == 0:
        return submitted.strftime('%H:%M:%S')
    elif 0 < days_ago <= 6:
        return submitted.strftime('%a %H:%M')
    elif submitted.year == today.year:
        return submitted.strftime('%b %d %H:%M')
    else:
        return submitted.strftime('%Y-%m-%d')


# ----------------------------------------------------------------------
# Doctests

if __name__ == "__main__":
    import doctest
    doctest.testmod(
        extraglobs={},
        verbose=True,
        optionflags=doctest.ELLIPSIS,
    )
