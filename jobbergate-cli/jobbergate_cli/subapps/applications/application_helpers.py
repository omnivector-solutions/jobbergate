"""
Helper functions that may be used inside of Jobbergate applications.
"""
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
    """Returns a list of input files in a directory ( default: pwd)."""
    if not path:
        path = Path.cwd()

    file_paths = sorted(path.glob(search_term), key=lambda p: p.stat().st_mtime, reverse=True)
    file_names = [f.name for f in file_paths if f.is_file()]
    return file_names
