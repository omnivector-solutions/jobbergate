#!/bin/bash

#SBATCH --job-name={{data.job_name}}
#SBATCH --partition={{data.partition}}
#SBATCH --output=sample-%j.out


echo $SLURM_TASKS_PER_NODE
echo $SLURM_SUBMIT_DIR