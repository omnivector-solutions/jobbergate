#!/bin/bash

#SBATCH -J dummy_job
#SBATCH -t 60

echo "Executing simple job script"

echo "Simple output from $HOSTNAME" > simple-output.txt
