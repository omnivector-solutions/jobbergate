import datetime
import pathlib
import re
import shutil
import toml

# Configuration file for the Sphinx documentation builder.

# -- Project information -----------------------------------------------------

docs_root = pathlib.Path(__file__).parent
project_root = docs_root.parent
project_metadata = toml.load(project_root / "pyproject.toml")["tool"]["poetry"]

_ptrn = r"(.*)<.*>"
_repl = r"\1"
author = ", ".join([re.sub(_ptrn, _repl, a) for a in project_metadata["authors"]])
project = project_metadata["name"]
copyright = project_metadata.get("copyright", str(datetime.datetime.now().year))
repo_url = project = project_metadata["repository"]
version = project_metadata["version"]
release = project_metadata["version"]


# -- General configuration ---------------------------------------------------

master_doc = "index"
templates_path = ["_templates"]
smartquotes = False
pygments_style = "rainbow_dash"
exclude_patterns = []
extensions = [
    "sphinx.ext.githubpages",
    "sphinxcontrib.httpdomain",
]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_book_theme"
html_theme_options = {
    "repository_url" : repo_url,
    "use_repository_button": True,
    "use_issues_button": True,
}
html_logo = "images/logo.png"
html_title = project_metadata["description"]
