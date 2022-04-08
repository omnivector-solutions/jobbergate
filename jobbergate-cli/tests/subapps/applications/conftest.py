import contextlib
import os
import pathlib

import pytest


@pytest.fixture
def temp_cd():
    @contextlib.contextmanager
    def _helper(path: pathlib.Path):
        """
        Helper method to temporarily change directory.
        Pretty much copied from:
        https://dev.to/teckert/changing-directory-with-a-python-context-manager-2bj8
        """
        anchor = pathlib.Path().absolute()
        try:
            os.chdir(path)
            yield
        finally:
            os.chdir(anchor)

    return _helper
