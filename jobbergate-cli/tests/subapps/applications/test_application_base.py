import pathlib

from jobbergate_cli.subapps.applications.application_base import JobbergateApplicationBase


class DummyApplication(JobbergateApplicationBase):
    def mainflow(self):
        pass


def test_find_templates(tmp_path):
    application_path = tmp_path / "dummy"
    assert JobbergateApplicationBase.find_templates(application_path) == []

    application_path.mkdir()
    template_root_path = application_path / "templates"
    template_root_path.mkdir()
    file1 = template_root_path / "file1"
    file1.write_text("foo")
    file2 = template_root_path / "file2"
    file2.write_text("bar")
    dir1 = template_root_path / "dir1"
    dir1.mkdir()
    file3 = dir1 / "file3"
    file3.write_text("baz")
    assert JobbergateApplicationBase.find_templates(application_path) == [
        pathlib.Path("templates/dir1/file3"),
        pathlib.Path("templates/file1"),
        pathlib.Path("templates/file2"),
    ]


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
