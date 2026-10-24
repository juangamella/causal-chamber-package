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

"""This module renders the Remote Lab dashboard, i.e., the panels
with the user's account, the chambers, and the user's active sessions
and experiments, from the account returned by GET /v1/account.

All timestamps returned by the API are in seconds since the epoch
(UTC); they are shown in the local timezone of the machine.
"""

# Packages from the standard library
import math
import time
from datetime import datetime

# Third-party packages
from rich import box
from rich.console import Console, Group
from rich.measure import Measurement
from rich.padding import Padding
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

# Imports from this package
from causalchamber import _PROMPT_STYLE, _CODE_STYLE

# --------------------------------------------------------------------
# Layout and styles

# Indentation of the whole dashboard, in columns
_INDENT = 1
# Minimum width of the dashboard (without the indentation), in columns
_MIN_WIDTH = 116
# Width of the Account panel
_ACCOUNT_WIDTH = 38
# Minimum number of lines inside the Account and Chambers panels,
# which are shown side by side and have the same height
_MIN_TOP_ROW_LINES = 10
# Maximum number of waiting (submitting or queued) experiments shown
_MAX_WAITING = 6
# Width of the progress bars
_BAR_WIDTH = 13

# Colors of the dashboard design (Claude Design hand-off), made for a
# dark background. Default text keeps the terminal's own color.
_DIM_STYLE = "#6c6f73"        # dim / secondary text
_MUTED_STYLE = "#9b9da0"      # muted labels and headers
_BORDER_STYLE = "#3b3e43"     # panel borders, dotted separator
_BAR_TRACK_STYLE = "#3b3e43"  # empty part of the progress bars
_GREEN = "#73c47f"            # ready, running, credits
_YELLOW = "#dcbc63"           # busy, queued
_CYAN = "#79bfe0"             # submitting, 'yours'
_ORANGE = "#e0956a"           # stopping
_INK = "#121315"              # text of the 'rlab' badge
_HEADER_STYLE = f"bold {_MUTED_STYLE}"

# Icon, label and style of each experiment status
_EXPERIMENT_STATUS = {
    'RUNNING': ('▶', 'running', _GREEN),
    'STOPPING': ('■', 'stopping', _ORANGE),
    'SUBMITTING': ('↑', 'submitting', _CYAN),
    'QUEUED': ('◦', 'queued', _YELLOW),
}
_IN_FLIGHT = ('RUNNING', 'STOPPING')

# Style of each chamber state
_CHAMBER_STATE_STYLE = {'ready': _GREEN, 'busy': _YELLOW, 'offline': _DIM_STYLE}

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
    renderable, width = _render(account, time.time(), Console())
    # Print at the dashboard's own width: if the terminal is narrower,
    # its lines overflow (as with print()) instead of being cropped
    Console(highlight=False, width=width).print(renderable)


# TODO (step 3 of plan.md): implement the functions below

def run_monitor(fetch_account, refresh_rate):
    """Show the dashboard live, fetching the account with
    fetch_account() every refresh_rate seconds, until Ctrl+C."""
    raise NotImplementedError("Lab.monitor is not implemented yet")


def print_chamber(chamber, user_id, print_max=10):
    """Print the details of a chamber, as returned by GET
    /v1/chambers/{chamber_id}."""
    raise NotImplementedError("Printing a chamber is not implemented yet; use verbose=False")


def print_experiments(experiments):
    """Print the given experiments, as returned by GET
    /v1/experiments."""
    raise NotImplementedError("Printing experiments is not implemented yet; use verbose=False")


# --------------------------------------------------------------------
# Rendering

def _render(account, now, console):
    """
    Return the dashboard for the given account as a rich renderable,
    together with the width (in columns) it should be printed at.

    The whole dashboard is indented by one space, with a blank line
    before and after it. The Account and
    Chambers panels are shown side by side, unless the console is a
    terminal too narrow for that but wide enough for the dashboard
    with the two panels stacked. If the dashboard does not fit either
    way, it is wider than the terminal and its lines overflow.
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
    header, header_width = _header(account, now)
    wide_width = max(_MIN_WIDTH, _ACCOUNT_WIDTH + 1 + chambers_width, sessions_width, experiments_width)
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
    renderable = Group(header, "", top, "", sessions_panel, "", experiments_panel, "", _footer())
    # Indent the dashboard, with a blank line before and after it
    return Padding(renderable, (1, 0, 1, _INDENT)), width + _INDENT


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


def _header(account, now):
    """Return the header line (the title, the user ID and the current
    local date and time) and the width it needs."""
    left = Text.assemble((" rlab ", f"bold {_INK} on {_PROMPT_STYLE}"),
                         "  Causal Chamber® | ",
                         ("Remote Lab", "bold"),
                         (f"  {account.get('user_id') or ''}", _DIM_STYLE))
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
    return footer


def _account_body(account):
    """Return the contents of the Account panel and its number of
    lines. Unless the credits are unlimited, it ends with how to top
    them up."""
    wallet = account.get('wallet') or {}
    grid = Table.grid()
    grid.add_column(width=12, style=_DIM_STYLE)
    grid.add_column(no_wrap=True, overflow="ellipsis")
    rows = [("name", account.get('name')),
            ("user id", account.get('user_id')),
            ("email", account.get('email')),
            None,
            ("institution", account.get('institution')),
            ("academic", account.get('is_academic')),
            None]
    for row in rows:
        grid.add_row(*(("", "") if row is None else (row[0], _value(row[1]))))
    grid.add_row("credits", Text(_fmt_credits(wallet), style=_GREEN))
    unlimited = 'credit_floor' in wallet and wallet['credit_floor'] is None
    if unlimited:
        return grid, len(rows) + 1
    grid.add_row("", "")
    body = Group(grid, Text("Top up your credits with:", style=_DIM_STYLE), _prompt("rlab.topup()"))
    return body, len(rows) + 4


def _chambers_panel(chambers, sessions, now, lines):
    """Return the Chambers panel, with the given number of lines inside
    it, and the width it needs.

    The chambers are sorted with the ready ones first, then the busy
    ones by when they become available, then those held by the user's
    own sessions, then the offline ones.
    """
    own = {session.get('chamber_id') for session in sessions}
    n_ready = sum(chamber.get('state') == 'ready' for chamber in chambers)
    count = f"{n_ready} / {len(chambers)} ready"
    if len(chambers) == 0:
        body = Text("No chambers available.", style=_DIM_STYLE)
        return (_panel(body, "Chambers", count, height=lines + 2),
                _panel_width(body, "Chambers", count))
    subtitle = _prompt("rlab.get_queue(<id>)", "to see a chamber's queue")

    def order(chamber):
        state = chamber.get('state')
        group = {'ready': 0, 'busy': 1}.get(state, 3)
        if state == 'busy' and chamber.get('chamber_id') in own:
            group = 2
        return (group, chamber.get('available_on') or 0, chamber.get('chamber_id') or '')

    table = _table(["", "Chamber", "Model", "", "Mode", "Available on"])
    for chamber in sorted(chambers, key=order):
        state = chamber.get('state')
        style = _CHAMBER_STATE_STYLE.get(state, _DIM_STYLE)
        table.add_row(Text("●", style=style),
                      _value(chamber.get('chamber_id')),
                      _value(chamber.get('model'), _MUTED_STYLE),
                      Text(state or _MISSING, style=style),
                      _value(chamber.get('mode'), _MUTED_STYLE),
                      _fmt_available(chamber, chamber.get('chamber_id') in own, now))
    return (_panel(table, "Chambers", count, subtitle, height=lines + 2),
            _panel_width(table, "Chambers", count, subtitle))


def _sessions_panel(sessions, now):
    """Return the Sessions panel and the width it needs."""
    count = f"{len(sessions)} active"
    if len(sessions) == 0:
        body = Text("No active sessions.", style=_DIM_STYLE)
        return _panel(body, "Sessions", count), _panel_width(body, "Sessions", count)
    table = _table(["", "Session ID", "Chamber", "Config", "Expires"])
    for session in sessions:
        table.add_row(Text("●", style=f"blink {_GREEN}"),
                      _value(session.get('session_id')),
                      _value(session.get('chamber_id')),
                      _value(session.get('chamber_config')),
                      _fmt_expires(session.get('expires_on'), now))
    subtitle = _prompt("rlab.stop_session(<id>)")
    return (_panel(table, "Sessions", count, subtitle),
            _panel_width(table, "Sessions", count, subtitle))


def _experiments_panel(experiments, now):
    """Return the Experiments panel and the width it needs.

    The in-flight experiments (running or stopping) are shown first,
    followed by a dotted line and the waiting ones (submitting, then
    queued). At most _MAX_WAITING waiting experiments are shown; the
    rest are summarized as '+ N more queued'.
    """
    in_flight = [e for e in experiments if e.get('status') in _IN_FLIGHT]
    waiting = ([e for e in experiments if e.get('status') == 'SUBMITTING'] +
               [e for e in experiments if e.get('status') not in _IN_FLIGHT + ('SUBMITTING',)])
    count = f"{len(in_flight)} in flight · {len(waiting)} waiting"
    subtitle = _prompt("rlab.get_experiments()", "for all")
    if len(experiments) == 0:
        body = Text("No active experiments.", style=_DIM_STYLE)
        return (_panel(body, "Experiments", count, subtitle),
                _panel_width(body, "Experiments", count, subtitle))
    headers = ["Status", "Progress", "Runtime", "Experiment ID", "Tag", "Chamber", "Config", "Submitted"]
    in_flight_rows = [_experiment_row(e, now) for e in in_flight]
    waiting_rows = [_experiment_row(e, now) for e in waiting[0:_MAX_WAITING]]
    # The in-flight and waiting experiments are in separate tables
    # (with a dotted line in between), with the same column widths
    widths = [max(len(header), *(row[i].cell_len for row in in_flight_rows + waiting_rows))
              for i, header in enumerate(headers)]
    parts = []
    for rows in [in_flight_rows, waiting_rows]:
        if len(rows) == 0:
            continue
        if len(parts) > 0:
            parts.append(Rule(characters="┄", style=_BORDER_STYLE))
        table = _table(headers, right_justified=[2], widths=widths, show_header=len(parts) == 0)
        for row in rows:
            table.add_row(*row)
        parts.append(table)
    if len(waiting) > _MAX_WAITING:
        parts.append(Text(f"+ {len(waiting) - _MAX_WAITING} more queued", style=_DIM_STYLE))
    body = Group(*parts)
    return (_panel(body, "Experiments", count, subtitle),
            _panel_width(body, "Experiments", count, subtitle))


def _experiment_row(experiment, now):
    """Return the cells (rich Text) of the row of the given experiment
    in the Experiments panel."""
    status = experiment.get('status')
    icon, label, style = _EXPERIMENT_STATUS.get(status, ("•", str(status).lower(), ""))
    if status in _IN_FLIGHT:
        progress = _progress_bar(experiment, style)
    elif status == 'SUBMITTING':
        progress = Text("starting now", style=_CYAN)
    else:
        progress = Text("")
    submitted_on = experiment.get('submitted_on')
    # The icon blinks (in terminals that support it), as the experiment is active
    return [Text.assemble((icon, f"blink {style}"), (f" {label}", style)),
            progress,
            _fmt_runtime(experiment, now),
            _value(experiment.get('experiment_id')),
            _value(experiment.get('tag'), _MUTED_STYLE),
            _value(experiment.get('chamber_id')),
            _value(experiment.get('chamber_config'), _MUTED_STYLE),
            Text(_MISSING if submitted_on is None else _fmt_submitted(submitted_on, now), style=_DIM_STYLE)]


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
    >>> _fmt_available({'state': 'ready'}, own=False, now=0).plain
    'now'
    >>> _fmt_available({'state': 'busy', 'mode': 'queue', 'available_on': 540}, own=False, now=0).plain
    '...  in ~9 min'
    >>> _fmt_available({'state': 'busy', 'mode': 'real-time', 'available_on': 2584800}, own=True, now=0).plain
    '...  in 29d 22h  yours'
    >>> _fmt_available({'state': 'offline', 'available_on': None}, own=False, now=0).plain
    '—'
    """
    state = chamber.get('state')
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
