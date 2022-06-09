import os
import shlex

from jobbergate_cli.subapps.applications.application_helpers import get_file_list, get_running_jobs
from jobbergate_cli.text_tools import dedent_all


def test_get_running_jobs(mocker):
    """
    Test that the ``get_running_jobs()`` funciton gets a list of running jobs (and the users) from squeue.

    Assert that the ``user_only`` argument is handled correctly. Also verify that if an exception is thrown
    or if the squeue command fails an empty list is returned.
    """
    mocker.patch(
        "jobbergate_cli.subapps.applications.application_helpers.getuser",
        return_value="dummy-user",
    )
    mocked_subprocess = mocker.patch("jobbergate_cli.subapps.applications.application_helpers.subprocess")
    mocked_run = mocked_subprocess.run

    mocked_output = mocker.MagicMock()
    mocked_output.stdout = dedent_all(
        """
              77 foo
              88 bar
              99 "baz bazzington"
        """,
        "",  # For the extra newline!
    ).encode("utf-8")

    mocked_run.return_value = mocked_output

    assert get_running_jobs() == [
        "77 foo",
        "88 bar",
        "99 baz bazzington",
    ]
    mocked_run.assert_called_once_with(
        shlex.split("""squeue --format="%.8A %j" --noheader --user=dummy-user"""),
        capture_output=True,
        check=True,
    )

    mocked_run.reset_mock()

    get_running_jobs(user_only=False)
    mocked_run.assert_called_once_with(
        shlex.split("""squeue --format="%.8A %j" --noheader"""),
        capture_output=True,
        check=True,
    )

    mocked_run.reset_mock()
    mocked_run.side_effect = RuntimeError("BOOM!")

    assert get_running_jobs() == []


def test_get_file_list__basic(tmp_path, temp_cd):
    """
    Test that the ``get_file_list()`` method returns a list of files in a path matching some search term.

    Assert that the function works with no arguments, with only the target path, and with the search term.
    Also assert that case is ignored.
    """
    file1 = tmp_path / "file1.py"
    file1.write_text("foo")
    os.utime(file1, (0, 2))

    file2 = tmp_path / "FILE2.txt"
    file2.write_text("bar")
    os.utime(file2, (0, 3))

    dir1 = tmp_path / "dir1"
    dir1.mkdir()

    file3 = dir1 / "file3.py"
    file3.write_text("baz")
    os.utime(file3, (0, 1))

    with temp_cd(tmp_path):
        assert get_file_list() == [
            "FILE2.txt",
            "file1.py",
        ]

    assert get_file_list(tmp_path) == [
        "FILE2.txt",
        "file1.py",
    ]

    assert get_file_list(tmp_path, search_term="*") == [
        "FILE2.txt",
        "file1.py",
    ]

    assert get_file_list(tmp_path, search_term="*.py") == [
        "file1.py",
    ]

    assert get_file_list(tmp_path, search_term="*FILE*") == [
        "FILE2.txt",
        "file1.py",
    ]
