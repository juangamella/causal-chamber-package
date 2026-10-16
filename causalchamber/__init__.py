import os
import sys

__all__ = ["datasets", "utils", "ground_truth", "simulators"]

# --------------------------------------------------------------------
# Welcome message, displayed on import in interactive sessions
# (Jupyter, IPython or a terminal) unless CAUSALCHAMBER_QUIET is set

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
    from rich.console import Console
    from rich.markup import escape

    try:
        title = f"Causal Chamber® v{version('causalchamber')}"
    except PackageNotFoundError:
        # e.g., when running from source without installing the package
        title = "Causal Chamber®"
    # No borders/panels around the citation so it can be copy-pasted
    citation = "\n".join("    " + line for line in _CITATION.splitlines())
    email = "support@causalchamber.ai"
    docs = "docs.causalchamber.ai"
    console = Console(highlight=False)
    console.print(
        f"""
[bold]{escape(title)}[/bold]

  [bold]Login[/bold]

    To log into the Remote Lab, call

      >>> import causalchamber.lab as lab
      >>> lab.login()

  [bold]Documentation[/bold]

    Guides and examples at [link=https://{docs}]{docs}[/link]

  [bold]Support[/bold]

    Issues or feedback? Write us at [link=mailto:{email}]{email}[/link]

  [bold]Citation[/bold]

    If you use our datasets, simulators or Remote Lab for your work, please consider citing:

{escape(citation)}

  [dim]Set the env. variable CAUSALCHAMBER_QUIET=1 to hide this message.[/dim]
""",
        soft_wrap=True,
    )


if os.environ.get("CAUSALCHAMBER_QUIET", "") in ("", "0") and _is_interactive():
    _print_welcome_message()
