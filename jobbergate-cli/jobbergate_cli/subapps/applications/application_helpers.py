"""
Helper functions that may be used inside of Jobbergate applications.
"""
import shlex
import subprocess
from getpass import getuser
import os, re, fnmatch


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


def get_file_list(path=".", search_term="*.*"):
    """Returns a list of input files in a directory ( default: pwd)."""
    all_paths = os.listdir(path)
    pattern = re.compile(fnmatch.translate(search_term), re.IGNORECASE)

    file_paths = [p for p in all_paths if os.path.isfile(os.path.join(path, p)) and re.match(pattern, p)]
    file_paths = sorted(file_paths, key=lambda p: os.stat(os.path.join(path, p)).st_mtime, reverse=True)
    return file_paths
