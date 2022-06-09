"""
Helper functions that may be used inside of Jobbergate applications.
"""
import fnmatch
import re
import shlex
import subprocess
from getpass import getuser
from pathlib import Path


def get_running_jobs(user_only=True):
    """
    Return a list of the user's currently running jobs, as given by SLURM's squeue command.

    The format returned is: [job ID, 8 chars] [job name]
    """
    cmd_args = shlex.split("""squeue --format="%.8A %j" --noheader""")
    if user_only:
        cmd_args.append(f"--user={getuser()}")
    try:
        cmd_results = subprocess.run(cmd_args, capture_output=True, check=True)
        # Skip last line (empty), strip quotation marks
        output_lines = cmd_results.stdout.decode("utf-8").strip().split("\n")
        ID_alternatives = [ln.replace('"', "").strip() for ln in output_lines]
    except Exception:
        print("Could not retrieve queue information from SLURM.")
        return []
    return ID_alternatives


def get_file_list(path=None, search_term="*.*"):
    """
    Return a list of input files in a directory that match a search term.

    Ignore casing when comparing against the search term.

    Default to searching for all files in the current directory.
    """
    if not path:
        path = Path.cwd()

    pattern = re.compile(fnmatch.translate(search_term), re.IGNORECASE)
    file_paths = [p for p in path.iterdir() if p.is_file() and re.match(pattern, p.name)]
    file_paths = sorted(file_paths, key=lambda p: p.stat().st_mtime, reverse=True)
    return [p.name for p in file_paths]
