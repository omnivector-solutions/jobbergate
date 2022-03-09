import contextlib
import os
import pathlib

import pytest

from jobbergate_cli.application_base import JobbergateApplicationBase


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


class DummyApplication(JobbergateApplicationBase):

    def mainflow(self):
        pass


def test_get_template_files(temp_cd, tmp_path):

    templates_path = tmp_path / "templates"
    templates_path.mkdir()
    template1 = templates_path / "template1.j2"
    template1.write_text("template1")
    template2 = templates_path / "template2.j2"
    template2.write_text("template2")

    subdir_path = templates_path / "subdir"
    subdir_path.mkdir()
    template3 = subdir_path / "template3.j2"
    template3.write_text("template3")

    with temp_cd(tmp_path):
        dummy = DummyApplication(
            dict(
                jobbergate_config=dict(),
                application_config=dict(),
            )
        )
        template_file_paths = dummy.get_template_files()
        assert pathlib.Path("templates/template1.j2") in template_file_paths
        assert pathlib.Path("templates/template2.j2") in template_file_paths
        assert pathlib.Path("templates/subdir/template3.j2") in template_file_paths
