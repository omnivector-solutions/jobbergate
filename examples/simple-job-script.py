#!/bin/python3

#SBATCH -J dummy_job
#SBATCH -t 60

from pathlib import Path
from socket import gethostname

print("Executing simple job script")

output_file = Path(f"simple-output.txt")
output_file.write_text(f"Simple output from {gethostname()}")
