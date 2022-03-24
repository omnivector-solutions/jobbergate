#!/bin/python3

# - Generic information - #
# Job name
#SBATCH -J PG_03
# Job time limit in minutes
#SBATCH -t 300
# Asks SLURM to send a USR1 signal 2 hours before end of the time limit
#SBATCH --signal=B:USR1@7200
# Which partitions to use
#SBATCH --partition compute
# Name of account (not user) for accounting.
#SBATCH -A abaqus
# Licenses required, appointed to master job
#SBATCH --licenses abaqus.abaqus@flexlm:22

# - Type-specific information - #
# An email is sent at the start and end
#SBATCH --mail-type=BEGIN,END

# - Jobpack 1 - #
# Nodes to use - always one master node
#SBATCH -N 1

# Memory requirement on master node
#SBATCH --mem=340G

# Exclusive execution on head node
#SBATCH --exclusive

# Import required python modules
import os
import sys
import re
import subprocess
import shutil
import pwd
import json
from pathlib import Path
import signal
import time

# Import processManager from temp folder, TODO clean up!
sys.path.append("/grp/techsim/applications_techsim/Abaqus/Projects/SubmitScript/Test/")
from processManager import processManager  # noqa E402


def parse_slurm_nodes(hostlist):
    """ Takes a contracted hostlist string and returns an expanded list.
        e.g.: "node[1,3-4]" -> ["node1", "node3", "node4"]
    """
    cmd_args = ['scontrol', 'show', 'hostnames', hostlist]
    try:
        cmd_results = subprocess.run(cmd_args, stdout=subprocess.PIPE)
        # Skip last line (empty), strip quotation marks
        expanded_hostlist = cmd_results.stdout.decode().strip().split("\
")
        return expanded_hostlist
    except BaseException:
        print("Could not retrieve queue information from SLURM.")
        return []


# Set debug mode for additional output
debug = False

# Project is the name of the script and template
PROJECT = "abaqus-solve-eigenfreqency"

# Get job information from SLURM
JOB_NAME = os.getenv('SLURM_JOB_NAME')
HOSTNAME = os.getenv('HOSTNAME')
USER = os.getenv('USER')
JOB_ID = os.getenv('SLURM_JOBID')
STARTDIR = os.getenv('SLURM_SUBMIT_DIR')
WORKDIR = f'/scratch/{USER}/abaqus_job_{JOB_ID}'
ENDDIR = STARTDIR

# Logging
exit_status = ""

# Unset variable to avoid strange bug
if "SLURM_GTIDS" in os.environ:
    del os.environ['SLURM_GTIDS']

# Get compute hosts and total number of CPUs

LSB_MCPU_HOSTS = ''
cpus = 0
HOST_SPLIT = 1
# Suffix to translate from slurm's nodename to full hostname for Abaqus. WARNING: node hostnames need to be consistent.
HOST_SUFFIX = "." + os.environ['SLURM_SUBMIT_HOST'].split(".", 1)[-1]
print("Nodes:")
if 'SLURM_PACK_SIZE' in os.environ:
    sys.exit(f' ERROR: Abaqus Eigenfreqency jobs may not be distributed on several nodes, exiting!')
else:
    for host in parse_slurm_nodes(os.getenv('SLURM_JOB_NODELIST')):
        print(host)
        LSB_MCPU_HOSTS += f"{host}{HOST_SUFFIX} {os.getenv('SLURM_CPUS_ON_NODE')} "
        cpus += int(os.getenv('SLURM_CPUS_ON_NODE'))



def _logging():
    log_comment = "NA"

    # Have Abaqus summarize
    try:
        summaryfolder = Path(f"/grp/techsim/applications_techsim/Abaqus/Projects/summaries_SLURM//{JOB_ID}")
        summaryfolder.mkdir(parents=True, exist_ok=True)  # Make dir if it doesn't exist

        cmd = f"ABQLauncher summarize job={JOB_NAME}".split()
        try:
            summary_result = subprocess.run(cmd, cwd=WORKDIR, env=module_env, stdout=subprocess.PIPE)
            print(f"Abaqus summary completed with code {str(summary_result.returncode)}")
        except Exception as why:
            print("Abaqus could not create summary file: " + str(why).split('\
')[-1])

        # Copy .use file and other log files to summary folder
        usefile = os.path.join(WORKDIR, JOB_NAME + ".use")
        logfiles = [
            usefile,
            os.path.join(WORKDIR, JOB_NAME + ".log"),
            os.path.join(WORKDIR, JOB_NAME + "_summary.xml")
        ]
        for file in logfiles:
            try:
                shutil.copy(file, summaryfolder)
            except IOError:
                print(f"Couldn't copy {file} to {summaryfolder}")

    except Exception as why:
        print("ERROR: could not create/populate summary folder: " + str(why).split('\
')[-1])

    try:
        # Parse .use-file for e.g. memory info
        with open(usefile, mode="r") as usefilehandle:
            contents = usefilehandle.read()

            timestamp = time.strftime("%Y-%m-%d_%H:%M", time.localtime())

            # Look for memory usage
            memory_re = re.compile(r"!Memory\\s*=\\s*(\\d+)", re.IGNORECASE)
            memory_searchresults = memory_re.search(contents)
            if memory_searchresults:
                used_memory = memory_searchresults.group(1)
            else:
                used_memory = -1

            # Determine std_error for logging. Innocent until proven guilty.
            std_error = False
            # 1 TODO Killed by user -> False
            # 2-3 SLURM timeout or process manager timeout
            # Use global variable
            global exit_status
            if "Killed" in exit_status:
                std_error = False
            else:
                # 4-6 Look for unfinished tags
                start_re = re.compile(r"([^\\s]*)-Start", re.IGNORECASE)
                starts = re.findall(start_re, contents)

                if "std" not in starts:
                    std_error = False
                else:
                    # std-Start is declared, keep looking
                    end_re = re.compile(r"([^\\s]*)-End", re.IGNORECASE)
                    ends = re.findall(end_re, contents)

                    # Eliminate matching start/end tags
                    index = 0
                    while index < len(ends):
                        try:
                            starts.remove(ends[index])
                            ends.remove(ends[index])
                        except ValueError:
                            # The element from 'ends' was not found in 'starts', move on
                            index += 1

                    # "Increment", "Attempt", "Iteration", and "Exec" tags can be ignored
                    starts = [s for s in starts if s != "Increment" and s != "Attempt" and s != "Iteration" and s != "Exec" and s != "ProcDriver"]
                    ends = [s for s in ends if s != "Increment" and s != "Attempt" and s != "Iteration" and s != "Exec" and s != "ProcDriver"]

                    if len(starts) > 0:
                        print(f".use file has the following tags left open: {', '.join(starts)}")
                        std_error = True
                        log_comment = starts[-1]
                    if len(ends) > 0:
                        print(f".use file tries to close the following tags, without opening them: {', '.join(ends)}")

    except IOError as why:
        print("ERROR: no .use file found: " + str(why).split('\
')[-1])
        std_error = True
        exit_status = "Exited"
        used_memory = -1
        timestamp = "?"
        log_comment = "(no .use file found)"

    # In case of std_error, make a copy of files for troubleshooting later.
    if std_error:
        debug_files = []
        # Input files, some result files and exception info
        extensions = ["*.inp", "*.inc", "*.geo", "*.geom", "*.misc", "*.use", "*.pre", "*.dat", "*.msg", "*.err", "*.sta", "*.exception"]
        for ext in extensions:
            debug_files.extend(list(Path(WORKDIR).glob(ext)))
        # Slurm output
        debug_files.append(f"{STARTDIR}/slurm-{JOB_ID}.out")

        # Make unique folder to place them in
        year = time.strftime("%Y")
        try:
            cluster = os.getenv("SLURM_SUBMIT_HOST").split(".")[0]
        except AttributeError:
            cluster = "s"
        DEBUGDIR = Path(f"/grp/techsim/applications_techsim/Abaqus/Projects/SolverProblems/std_error_slurm//{year}/{cluster}-{JOB_ID}/")
        print("std_error detected. Copying files to  " + str(DEBUGDIR), flush=True)
        oldmask = os.umask(0)  # Needed to give full folder permissisons
        DEBUGDIR.mkdir(parents=True, exist_ok=True)  # Make dir if it doesn't exist
        os.umask(oldmask)

        # Copy files
        for file in debug_files:
            try:
                shutil.copy(file, DEBUGDIR)
            except IOError:
                print(f"Could not copy {file} to debugging backup location.", flush=True)

    # Define analysis type [Linear | Non-linear | Eigenfreqency]
    analysistype = "Non-linear"

    # Log a row of metadata
    try:
        with open("/grp/techsim/applications_techsim/Abaqus/Projects/jobLog_SLURM.log", mode='a+') as summary_file:
            # exit_status = [Done | Killed (timeout) | Exited (other error codes)]
            summary_file.write(f"{JOB_ID}, {USER}, {exit_status}, {std_error}, abaqus/2021-6, {cpus}, 0, {HOST_SPLIT}, {used_memory}, {analysistype}, {timestamp}, {log_comment}\
")
    except IOError:
        print("ERROR: Could not write to log file (/grp/techsim/applications_techsim/Abaqus/Projects/jobLog_SLURM.log).")


def _stageup():
    # Temporary: making room for job before stageup. Problem: does not have permission to delete others' stuff.
    # ONLY DO THIS IF "SBATCH --exclusive" IS USED! (standard)
    # If you want to remove the exclusive flag for any reason, remove this too or you delete your other jobs on the same node.
    print("Deleting old files on the node, if possible.")
    cleaning_dir = "/scratch/*"
    hetjob_targeting = ""
    if "SLURM_PACK_SIZE" in os.environ:
        hetjob_targeting = f"--het-group=0-{int(os.environ['SLURM_PACK_SIZE'])-1}"
    cleaning_cmd = f"srun {hetjob_targeting} /bin/bash -c 'rm -rv {cleaning_dir}'"
    cleaning_results = subprocess.run(cleaning_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(cleaning_results.stdout.decode())
    # Create scratch folder
    try:
        os.makedirs(WORKDIR)
    except OSError:
        sys.exit(f'ERROR: Local scratch folder could not be created:\
    {WORKDIR}')

    # Create "link" executable
    scratchlink = Path(f'GOTO_{JOB_NAME}_{JOB_ID}_DIR.sh')
    with open(scratchlink, "w") as fh:
        fh.write("#!/bin/bash\
")
        fh.write("echo \\"SSHing to another node. 'exit' / 'logout' / Ctrl-D to return.\\"\
")
        fh.write(f'ssh -t {HOSTNAME} "cd {WORKDIR}; exec $SHELL -l"')
    scratchlink.chmod(0o755)

    # Stage required files to local scratch
    files_to_stage_up = ['/home/nsxbxc/Documents/abaqus/ex/test_buck/PG_03.inp', '/grp/techsim/chassicalc/material/material-01.txt']

    for stage_up_file in files_to_stage_up:
        try:
            shutil.copy(stage_up_file, WORKDIR)
        except (IOError, os.error) as why:
            print(f' ERROR: Stage up failed: \
     Source: {stage_up_file} \
     Target: {WORKDIR} \
     Problem: ' + str(why).split("\
")[-1], flush=True)


def _stageback():
    filenames = ['PG_03.pre', 'PG_03.dat', 'PG_03.msg', 'PG_03.sta', 'PG_03.use', 'PG_03.odb', 'PG_03.sim', 'PG_03.fil', 'PG_03.prt', 'PG_03.err', 'PG_03.log', 'PG_03.par', 'PG_03.pes']
    files_to_stage_back = [f'{WORKDIR}/{file}' for file in filenames]
    print('Staging back:', flush=True)

    for stage_back_file in files_to_stage_back:
        if not os.path.isfile(stage_back_file):
            print(f'     - Missing expected: {stage_back_file}', flush=True)
        else:
            print(f'     - {stage_back_file}', flush=True)
            target_file = os.path.join(ENDDIR, os.path.basename(stage_back_file))
            try:
                shutil.copy(stage_back_file, target_file)
                # CHange OWNer: sets group ID to 2410 (techsim). Needed since shutil.copy() does not include metadata like owners.
                os.chown(target_file, pwd.getpwnam(USER).pw_uid, 2410)
            except (IOError, os.error):
                backup_location = os.path.join('/cluster/sesonas13', f'{USER}/{JOB_ID}_{JOB_NAME}')
                print(f'FAILED: copying file to {target_file}. Removing copied files and placing them in {backup_location} instead. Placing link in working directory. ', flush=True)

                # Copy to backup location instead
                Path(backup_location).mkdir(parents=True, exist_ok=True)

                for stage_back_file in files_to_stage_back:
                    print(f'     - {stage_back_file}', flush=True)
                    if not os.path.isfile(stage_back_file):
                        print(f'     - Missing: {stage_back_file}', flush=True)
                    else:
                        target_file = os.path.join(backup_location, os.path.basename(stage_back_file))
                        try:
                            shutil.copy(stage_back_file, backup_location)
                            # CHange OWNer: sets group ID to 2410 (techsim). Needed since shutil.copy() does not include metadata like owners.
                            os.chown(target_file, pwd.getpwnam(USER).pw_uid, 2410)
                        except IOError as why:
                            sys.exit(' ERROR: could not copy to backup location:\
     Problem: ' + str(why).split("\
")[-1])

                # Removing the files that were copied to original target
                for file in files_to_stage_back:
                    target_file = os.path.join(ENDDIR, os.path.basename(file))
                    if os.path.isfile(target_file):
                        os.remove(str(target_file))

                # Make link to backup location
                clusterlink = Path(f'{JOB_NAME}_{JOB_ID}')
                if not clusterlink.exists():
                    clusterlink.symlink_to(backup_location)
                break
    print("Stageback complete", flush=True)


def _cleanup():
    # Remove leftover files from scratch
    cleaning_dir = WORKDIR
    hetjob_targeting = ""
    if "SLURM_PACK_SIZE" in os.environ:
        hetjob_targeting = f"--het-group=0-{int(os.environ['SLURM_PACK_SIZE'])-1}"
    print("Removing working directories:", flush=True)
    cleaning_cmd = f"srun {hetjob_targeting} /bin/bash -c 'rm -rv {cleaning_dir}'"
    cleaning_results = subprocess.run(cleaning_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(cleaning_results.stdout.decode())

    # Remove the scratchlink
    scratchlink = Path(f'GOTO_{JOB_NAME}_{JOB_ID}_DIR.sh')
    if scratchlink.exists():
        scratchlink.unlink()


# This will activate when SLURM sends a SIGUSR1 signal, defined by --signal option of #SBATCH header or srun call
def timeout_handler(signum, frame):
    # Copy .msg file before it's overwritten (known Abaqus bug when aborting)
    msg_file = f"{WORKDIR}/{JOB_NAME}.msg"
    if os.path.isfile(msg_file):
        try:
            shutil.copy(msg_file, f"{ENDDIR}/{JOB_NAME}_backup.msg")
            print(f"Saved a copy of .msg file as: {JOB_NAME}_backup.msg")
        except IOError as why:
            print("Could not save a copy of .msg file.")

    # 2 hours until kill signal: allow 90m for graceful termination, then try to clean up regardless.
    terminate_timeout = 5400  # 90m
    if signum == signal.SIGTERM:
        print("Shutdown by SLURM imminent, saving what can be saved", flush=True)
        terminate_timeout = 180
    elif signum == signal.SIGUSR1:
        print("Requested time is over, trying to clean up and entering grace period", flush=True)

    print(f"Sending Abaqus terminate signal, timeout: {terminate_timeout}s", flush=True)
    subprocess.run(f"ABQLauncher terminate job={JOB_NAME}".split(), cwd=WORKDIR, env=module_env)
    # Normal "scancel" without --batch sends to all child processess so Abaqus may already be killed
    start_time = time.time()
    while (time.time() - start_time) < terminate_timeout:
        try:
            os.kill(abaqus_process.pid, 0)
        except ProcessLookupError:
            # PID does not exist, exit loop
            break
        time.sleep(5)
    global exit_status
    exit_status = "Killed(SLURM)"  # Timeout code

    try:
        os.kill(abaqus_process.pid, 0)
        print("Abaqus did not respond to termination signal in time, using force.", flush=True)
        processManager.kill_child_processes(abaqus_process)
    except Exception as e:
        print(f"Abaqus stopped successfully: {str(e)}", flush=True)
    _stageback()
    if signum == signal.SIGTERM:  # This may happen twice sometimes
        _logging()
        _cleanup()
    sys.exit("Job exit after timeout handling.")
signal.signal(signal.SIGUSR1, timeout_handler)  # noqa E305
signal.signal(signal.SIGTERM, timeout_handler)


try:
    _stageup()

    # Load application module into local env
    module_env = dict()
    module_abq = 'abaqus/2021-6'
    module_cmd = f'module use /share/apps/Modules/scania-applications; module load {module_abq}'
    dump_cmd = '/usr/bin/python -c "import os, json;print json.dumps(dict(os.environ))"'
    module_result = subprocess.run(['/bin/bash', '-c', f'{module_cmd} && {dump_cmd}'], stdout=subprocess.PIPE, timeout=10)
    module_out = module_result.stdout
    module_err = module_result.stderr

    if module_result.returncode != 0:
        sys.exit(f'ERROR: Abaqus module {module_abq} could not be loaded, exiting.\
    Module:{module_abq}\
    stdout: {module_out}\
    stderr: {module_err}')
    else:
        module_env = json.loads(module_out)

    # Assemble command line
    abaqus_cmd = [
        'ABQLauncher',  # TODO something else for 6.* versions? from /share/apps/abaqus/Linux/Commands/
        f'job={JOB_NAME}',
        f'input={os.path.basename("/home/nsxbxc/Documents/abaqus/ex/test_buck/PG_03.inp")}',
        'interactive',
        f'cpus={str(cpus)}',
        f'mp_host_split={str(HOST_SPLIT)}',
    ]

    # This lets Abaqus see and communicate with all allocated nodes
    module_env['LSB_MCPU_HOSTS'] = LSB_MCPU_HOSTS
    module_env['MPI_REMSH'] = 'ssh -x -q -o StrictHostKeyChecking=no'

    if debug:
        print("==== BEGIN ENVIRONMENT DUMP ====")
        for param in os.environ.keys():
            print(f'{param}: {os.environ[param]}')
        print("==== END ENVIRONMENT DUMP ====")

    # Launch application
    print(*abaqus_cmd, sep=" ", flush=True)

    try:
        with open(os.path.join(WORKDIR, f"{JOB_NAME}.err"), "w") as errorfile:
            abaqus_process = subprocess.Popen(abaqus_cmd, cwd=WORKDIR, env=module_env, stdout=subprocess.PIPE, stderr=errorfile)
            abaqus_result = processManager(abaqus_process, time_out=10800, check_timestamp=WORKDIR)
            outs, errs = abaqus_process.communicate(timeout=10)
            print(f"Abaqus output: {outs.decode()}", flush=True)
    except Exception as why:
        print("Abaqus block failed: " + str(why).split("\
")[-1], flush=True)
        try:  # Write Abaqus' error if available
            print(f"    - Abaqus error message: {errs.decode()}")
        except (NameError, AttributeError):
            pass

    try:
        if abaqus_result == 0:
            print("Abaqus was run successfully", flush=True)
            exit_status = "Done"
        elif abaqus_result == 17:
            print("Abaqus interrupted due to inactivity", flush=True)
            exit_status = "Killed(processManager)"
        else:
            print(f'Abaqus exited with ERROR CODE {abaqus_result}', flush=True)
            exit_status = "Exited"
    except NameError:
        print("Could not fetch Abaqus' error code.")
        exit_status = "Exited"
    # Stage back result files files from local scratch
    _stageback()
finally:
    _logging()
    _cleanup()"
