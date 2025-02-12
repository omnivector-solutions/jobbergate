import os
import sys


def detect_snap():
    return os.environ.get("SNAP") is not None


def restart_agent():
    python_bin = sys.executable
    os.execve(python_bin, [python_bin, *sys.argv], os.environ)
