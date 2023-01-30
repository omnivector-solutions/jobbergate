"""
Parser for Slurm REST API parameters from SBATCH parameters at the job script file.
"""
from argparse import ArgumentParser
from dataclasses import dataclass, field
from itertools import chain
from shlex import split
from typing import Any, Dict, List, Union

from bidict import bidict
from loguru import logger

from jobbergate_api.apps.job_scripts.job_script_files import JobScriptFiles
from jobbergate_api.apps.job_submissions.schemas import JobProperties

_IDENTIFICATION_FLAG = "#SBATCH"
_INLINE_COMMENT_MARK = "#"


def _flagged_line(line: str) -> bool:
    """
    Identify if a provided line starts with the identification flag.
    """
    return line.startswith(_IDENTIFICATION_FLAG)


def _clean_line(line: str) -> str:
    """
    Clean the provided line.

    It includes removing the identification flag at the beginning of the line,
    then remove the inline comment mark and anything after it, and finally strip white spaces at both sides.
    """
    return line.lstrip(_IDENTIFICATION_FLAG).split(_INLINE_COMMENT_MARK)[0].strip()


def _clean_jobscript(jobscript: str) -> List[str]:
    """
    Transform a job script string.

    It is done by filtering only the lines that start with
    the identification flag and mapping a cleaning procedure to them in order
    to remove the identification flag, remove inline comments, and strip extra
    white spaces. Finally, split each pair of parameter/value and chain them
    in a single list.
    """
    jobscript_filtered = filter(_flagged_line, jobscript.splitlines())
    jobscript_cleaned = map(_clean_line, jobscript_filtered)
    jobscript_splitted = map(split, jobscript_cleaned)
    return list(chain.from_iterable(jobscript_splitted))


@dataclass(frozen=True)
class SbatchToSlurm:
    """
    Store the information for each parameter, including its name at Slurm API and SBATCH.

    Besides that, any extra argument this parameter needs when added to
    the parser. This information is used to build the jobscript/SBATCH parser
    and the two-way mapping between Slurm API and SBATCH names.
    """

    slurmrestd_var_name: str
    sbatch: str
    sbatch_short: str = ""
    argparser_param: dict = field(default_factory=dict)


sbatch_to_slurm_mapping = [
    SbatchToSlurm("account", "--account", "-A"),
    SbatchToSlurm("account_gather_frequency", "--acctg-freq"),
    SbatchToSlurm("array", "--array", "-a"),
    SbatchToSlurm("batch_features", "--batch"),
    SbatchToSlurm("burst_buffer", "--bb"),
    SbatchToSlurm("", "--bbf"),
    SbatchToSlurm("begin_time", "--begin", "-b"),
    SbatchToSlurm("current_working_directory", "--chdir", "-D"),
    SbatchToSlurm("cluster_constraints", "--cluster-constraint"),
    SbatchToSlurm("", "--clusters", "-M"),
    SbatchToSlurm("comment", "--comment"),
    SbatchToSlurm("constraints", "--constraint", "-C"),
    SbatchToSlurm("", "--container"),
    SbatchToSlurm("", "--contiguous", "", dict(action="store_const", const=True)),
    SbatchToSlurm("core_specification", "--core-spec", "-S", dict(type=int)),
    SbatchToSlurm("cores_per_socket", "--cores-per-socket", "", dict(type=int)),
    SbatchToSlurm("cpu_binding", "--cpu-bind"),
    SbatchToSlurm("cpu_frequency", "--cpu-freq"),
    SbatchToSlurm("cpus_per_gpu", "--cpus-per-gpu"),
    SbatchToSlurm("cpus_per_task", "--cpus-per-task", "-c", dict(type=int)),
    SbatchToSlurm("deadline", "--deadline"),
    SbatchToSlurm("delay_boot", "--delay-boot", "", dict(type=int)),
    SbatchToSlurm("dependency", "--dependency", "-d"),
    SbatchToSlurm("distribution", "--distribution", "-m"),
    SbatchToSlurm("standard_error", "--error", "-e"),
    SbatchToSlurm("", "--exclude", "-x"),
    SbatchToSlurm(
        "exclusive",
        "--exclusive",
        "",
        dict(
            type=str,
            choices={"user", "mcs", "exclusive", "oversubscribe"},
            nargs="?",
            const="exclusive",
        ),
    ),
    SbatchToSlurm("", "--export"),
    SbatchToSlurm("", "--export-file"),
    SbatchToSlurm("", "--extra-node-info", "-B"),
    SbatchToSlurm("get_user_environment", "--get-user-env", "", dict(type=int)),
    SbatchToSlurm("", "--gid"),
    SbatchToSlurm("gpu_binding", "--gpu-bind"),
    SbatchToSlurm("gpu_frequency", "--gpu-freq"),
    SbatchToSlurm("gpus", "--gpus", "-G"),
    SbatchToSlurm("gpus_per_node", "--gpus-per-node"),
    SbatchToSlurm("gpus_per_socket", "--gpus-per-socket"),
    SbatchToSlurm("gpus_per_task", "--gpus-per-task"),
    SbatchToSlurm("gres", "--gres"),
    SbatchToSlurm("gres_flags", "--gres-flags"),
    SbatchToSlurm("", "--hint"),
    SbatchToSlurm("hold", "--hold", "-H", dict(action="store_const", const=True)),
    SbatchToSlurm("", "--ignore-pbs", "", dict(action="store_const", const=True)),
    SbatchToSlurm("standard_input", "--input", "-i"),
    SbatchToSlurm("name", "--job-name", "-J"),
    SbatchToSlurm(
        "kill_on_invalid_dependency", "--kill-on-invalid-dep", "", dict(type=bool, nargs="?", const=True)
    ),
    SbatchToSlurm("licenses", "--licenses", "-L"),
    SbatchToSlurm("mail_type", "--mail-type"),
    SbatchToSlurm("mail_user", "--mail-user"),
    SbatchToSlurm("mcs_label", "--mcs-label"),
    SbatchToSlurm("memory_per_node", "--mem"),
    SbatchToSlurm("memory_binding", "--mem-bind"),
    SbatchToSlurm("memory_per_cpu", "--mem-per-cpu"),
    SbatchToSlurm("memory_per_gpu", "--mem-per-gpu"),
    SbatchToSlurm("minimum_cpus_per_node", "--mincpus", "", dict(type=int)),
    SbatchToSlurm("", "--network"),
    SbatchToSlurm("nice", "--nice"),
    SbatchToSlurm("no_kill", "--no-kill", "-k", dict(action="store_const", const=True)),
    SbatchToSlurm("", "--no-requeue", "", dict(action="store_false", dest="requeue", default=None)),
    SbatchToSlurm("", "--nodefile", "-F"),
    SbatchToSlurm("", "--nodelist", "-w"),
    SbatchToSlurm("nodes", "--nodes", "-N"),
    SbatchToSlurm("tasks", "--ntasks", "-n", dict(type=int)),
    SbatchToSlurm("tasks_per_core", "--ntasks-per-core", "", dict(type=int)),
    SbatchToSlurm("", "--ntasks-per-gpu"),
    SbatchToSlurm("tasks_per_node", "--ntasks-per-node", "", dict(type=int)),
    SbatchToSlurm("tasks_per_socket", "--ntasks-per-socket", "", dict(type=int)),
    SbatchToSlurm("open_mode", "--open-mode"),
    SbatchToSlurm("standard_output", "--output", "-o"),
    SbatchToSlurm("", "--overcommit", "-O", dict(action="store_const", const=True)),
    SbatchToSlurm(
        "",
        "--oversubscribe",
        "-s",
        dict(action="store_const", const="oversubscribe", dest="exclusive"),
    ),
    SbatchToSlurm("", "--parsable", "", dict(action="store_const", const=True)),
    SbatchToSlurm("partition", "--partition", "-p"),
    SbatchToSlurm("", "--power"),
    SbatchToSlurm("priority", "--priority"),
    SbatchToSlurm("", "--profile"),
    SbatchToSlurm("", "--propagate"),
    SbatchToSlurm("qos", "--qos", "-q"),
    SbatchToSlurm("", "--quiet", "-Q", dict(action="store_const", const=True)),
    SbatchToSlurm("", "--reboot", "", dict(action="store_const", const=True)),
    SbatchToSlurm("requeue", "--requeue", "", dict(action="store_true", default=None)),
    SbatchToSlurm("reservation", "--reservation"),
    SbatchToSlurm("signal", "--signal"),
    SbatchToSlurm("sockets_per_node", "--sockets-per-node", "", dict(type=int)),
    SbatchToSlurm("spread_job", "--spread-job", "", dict(action="store_const", const=True)),
    SbatchToSlurm("", "--switches"),
    SbatchToSlurm("", "--test-only", "", dict(action="store_const", const=True)),
    SbatchToSlurm("thread_specification", "--thread-spec", "", dict(type=int)),
    SbatchToSlurm("threads_per_core", "--threads-per-core", "", dict(type=int)),
    SbatchToSlurm("time_limit", "--time", "-t"),
    SbatchToSlurm("time_minimum", "--time-min"),
    SbatchToSlurm("", "--tmp"),
    SbatchToSlurm("", "--uid"),
    SbatchToSlurm("", "--usage", "", dict(action="store_const", const=True)),
    SbatchToSlurm("minimum_nodes", "--use-min-nodes", "", dict(action="store_const", const=True)),
    SbatchToSlurm("", "--verbose", "-v", dict(action="store_const", const=True)),
    SbatchToSlurm("", "--version", "-V", dict(action="store_const", const=True)),
    SbatchToSlurm("", "--wait", "-W", dict(action="store_const", const=True)),
    SbatchToSlurm("wait_all_nodes", "--wait-all-nodes", "", dict(type=int)),
    SbatchToSlurm("wckey", "--wckey"),
    SbatchToSlurm("", "--wrap"),
]


class ArgumentParserCustomExit(ArgumentParser):
    """
    Custom implementation of the built-in class for argument parsing.

    The sys.exit triggered by the original code is replaced by a ValueError,
    besides some friendly logging messages.
    """

    def exit(self, status=0, message=None):
        """
        Raise ValueError when parsing invalid parameters or if the type of their values is not correct.
        """
        log_message = f"Argparse exit status {status}: {message}"
        if status:
            logger.error(log_message)
        else:
            logger.info(log_message)
        raise ValueError(message)


def build_parser() -> ArgumentParser:
    """
    Build an ArgumentParser to handle all SBATCH parameters declared at sbatch_to_slurm.
    """
    parser = ArgumentParserCustomExit()
    for item in sbatch_to_slurm_mapping:
        args = (i for i in (item.sbatch_short, item.sbatch) if i)
        parser.add_argument(*args, **item.argparser_param)

    return parser


def build_mapping_sbatch_to_slurm() -> bidict:
    """
    Create a mapper to translate in both ways between the names expected by Slurm REST API and SBATCH.
    """
    mapping: bidict = bidict()

    for item in sbatch_to_slurm_mapping:
        if item.slurmrestd_var_name:
            sbatch_name = item.sbatch.lstrip("-").replace("-", "_")
            mapping[sbatch_name] = item.slurmrestd_var_name

    return mapping


def jobscript_to_dict(jobscript: str) -> Dict[str, Union[str, bool]]:
    """
    Extract the SBATCH params from a given job script.

    It returns them in a dictionary for mapping the parameter names to their values.

    Raise ValueError if any of the parameters are unknown to the parser.
    """
    parsed_args, unknown_arg = parser.parse_known_args(args=_clean_jobscript(jobscript))

    if unknown_arg:
        raise ValueError("Unrecognized SBATCH arguments: {}".format(" ".join(unknown_arg)))

    sbatch_params = {key: value for key, value in vars(parsed_args).items() if value is not None}

    logger.debug(f"SBATCH params parsed from job script: {sbatch_params}")

    return sbatch_params


def convert_sbatch_to_slurm_api(input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Take a dictionary containing key-value pairing of SBATCH parameter name space to Slurm API namespace.

    Notice the values should not be affected.

    Raise KeyError if any of the keys are unknown to the mapper.
    """
    mapped = {}
    unknown_keys = []

    for sbatch_name, value in input.items():
        try:
            slurm_name = mapping_sbatch_to_slurm[sbatch_name]
            mapped[slurm_name] = value
        except KeyError:
            unknown_keys.append(sbatch_name)

    if unknown_keys:
        error_message = "Impossible to convert from SBATCH to Slurm REST API: {}"
        raise KeyError(error_message.format(", ".join(unknown_keys)))

    logger.debug(f"Slurm API params mapped from SBATCH: {mapped}")

    return mapped


def get_job_parameters(jobscript: str) -> Dict[str, Any]:
    """
    Parse all SBATCH parameters from a job script, map their names to Slurm API parameters.

    They are returned as a key-value pairing dictionary.
    """
    return convert_sbatch_to_slurm_api(jobscript_to_dict(jobscript))


def get_job_properties_from_job_script(job_script_id: int, **kwargs) -> JobProperties:
    """
    Get the job properties for Slurm REST API from a job script file, given its id.

    Extra keyword arguments can be used to overwrite any parameter from the
    job script, like name or current_working_directory.
    """
    job_script_files = JobScriptFiles.get_from_s3(job_script_id)
    slurm_parameters = get_job_parameters(job_script_files.main_file)
    merged_parameters = {**slurm_parameters, **kwargs}
    return JobProperties.parse_obj(merged_parameters)


parser = build_parser()
mapping_sbatch_to_slurm = build_mapping_sbatch_to_slurm()
