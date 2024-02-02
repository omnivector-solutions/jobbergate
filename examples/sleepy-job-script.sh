#!/bin/bash

#SBATCH -J dummy_job
#SBATCH -t 0:0:60

echo "Executing sleepy job script"
sleep 120
echo "Sleepy job script woke up"
