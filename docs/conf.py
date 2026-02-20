import os
import sys

# Add the package root to the path so autodoc can import causalchamber
sys.path.insert(0, os.path.abspath('..'))

project = 'Causal Chamber Lab'
copyright = '2025, Causal Chamber GmbH'
author = 'Juan L. Gamella'
release = '0.2.4'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
]

# Napoleon settings — docstrings use NumPy style
napoleon_numpy_docstring = True
napoleon_google_docstring = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = False
# Use :ivar: for Attributes sections so they don't conflict with @property docs
napoleon_use_ivar = True

# Autodoc settings
autodoc_member_order = 'bysource'
autodoc_default_options = {
    'members': True,
    'undoc-members': False,
    'private-members': False,
    'show-inheritance': True,
}

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'alabaster'
html_static_path = ['_static']
