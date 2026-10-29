import os
import sys

__all__ = ["datasets", "utils", "ground_truth", "simulators"]

# --------------------------------------------------------------------
# Welcome message, displayed on import in interactive sessions
# (Jupyter, IPython or a terminal) unless CAUSALCHAMBER_QUIET is set

# Styles (rich) of the Python prompt and code shown in printed messages
# (the banner, the Remote Lab dashboard, ...), as in the dashboard
# design (Claude Design hand-off), made for a dark background
_PROMPT_STYLE = "#e276b3"
_CODE_STYLE = "#79bfe0"

# The Python prompt, as rich markup
_PROMPT = f"[{_PROMPT_STYLE}]>>>[/]"


def _code(code):
    """Return the given code as rich markup, styled as code."""
    from rich.markup import escape

    return f"[{_CODE_STYLE}]{escape(code)}[/]"

_CITATION = r"""@article{gamella2025chamber,
  author={Gamella, Juan L. and Peters, Jonas and B{\"u}hlmann, Peter},
  title={Causal chambers as a real-world physical testbed for {AI} methodology},
  journal={Nature Machine Intelligence},
  doi={10.1038/s42256-024-00964-x},
  year={2025},
}"""


def _is_interactive():
    """Return True if running in Jupyter/IPython or with stdout attached to a terminal."""
    try:
        from IPython import get_ipython

        if get_ipython() is not None:
            return True
    except ImportError:
        pass
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


def _print_welcome_message():
    """Print the welcome message displayed on import."""
    from importlib.metadata import version, PackageNotFoundError
    from rich.console import Console, Group
    from rich.markup import escape
    from rich.padding import Padding
    from rich.table import Table

    try:
        title = f"  Causal Chamber® v{version('causalchamber')}"
    except PackageNotFoundError:
        # e.g., when running from source without installing the package
        title = "  Causal Chamber®"
    email = "support@causalchamber.ai"
    signup = "causalchamber.ai/get-started"
    docs = "docs.causalchamber.ai"
    # Two columns: section names (right-aligned) and their text
    # (left-aligned). A grid has no borders, so the citation can still
    # be copy-pasted; padding=(1, 2) leaves a blank line between
    # sections and two spaces between columns.
    sections = Table.grid(padding=(1, 2))
    sections.add_column(justify="right", style="bold")
    sections.add_column(justify="left")
    sections.add_row(
        "Login",
        "To log in to the Remote Lab, call\n\n"
        f"  {_PROMPT} {_code('from causalchamber import lab')}\n"
        f"  {_PROMPT} {_code('rlab = lab.login()')}",
    )
    sections.add_row(
        "Signup", f"Get your API credentials at [link=https://{signup}]{signup}[/link]"
    )
    sections.add_row(
        "Documentation", f"Guides and examples at [link=https://{docs}]{docs}[/link]"
    )
    sections.add_row(
        "Support", f"Issues or feedback? Write us at [link=mailto:{email}]{email}[/link]"
    )
    sections.add_row(
        "Citation",
        "If you use our datasets, simulators or Remote Lab for your work,\n"
        "please consider citing:\n\n"
        + f"[dim]{escape(_CITATION)}[/dim]",
    )
    # Print everything in a single call: in Jupyter, each call is
    # rendered as a separate output block, with large gaps between them
    console = Console(highlight=False)
    console.print(
        Group(
            "",
            f"[bold]{escape(title)}[/bold]",
            "",
            Padding(sections, (0, 0, 0, 2), expand=False),
            "",
            "  [dim]Set the env. variable CAUSALCHAMBER_QUIET=1 to hide this message.[/dim]",
            "",
        )
    )


if os.environ.get("CAUSALCHAMBER_QUIET", "") in ("", "0") and _is_interactive():
    _print_welcome_message()
