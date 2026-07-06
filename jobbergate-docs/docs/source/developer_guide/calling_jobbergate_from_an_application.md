# Calling Jobbergate from an application

The Jobbergate CLI commands (`job-scripts`, `applications`, and `job-submissions`)
are regular Python functions that can be imported and called directly. This is
especially useful inside a Workflow Source File (`jobbergate.py`), where application code
may need to create additional Job Scripts as part of its workflow.

Historically, this was done by shelling out to the CLI with `subprocess.run`, which spawned
a whole new CLI process for each call. Calling the commands as functions instead keeps
everything in-process, which means:

- Shared authentication and context: no need to log in again in a subprocess.
- Cached application data: the application details and workflow source code are cached
  in-process (per API client), so repeated or nested job-script creation does not
  re-download the same data.
- Better error handling: failures raise `jobbergate_cli.exceptions.Abort` (with the
  underlying exception available on `original_error`) instead of a non-zero exit code and
  captured stdout that needs to be parsed.
- Return values: commands return the resources they operate on (e.g. a `JobScriptResponse`)
  instead of text output.

!!! note "A word of moderation"

    Jobbergate applications were designed around a Question/Answer flow: gather a few
    answers from the user and render a job script from them. Calling Jobbergate from within
    an application script goes a step beyond that original intent -- workflow logic starts
    to live inside the application itself, adding complexity on the client side that the
    platform cannot see, validate, or manage for you. It is fully supported nonetheless,
    and sometimes it is the most practical option: a good example is the orchestration of a
    multi-step Slurm pipeline, where each step is created and submitted in a chain of Slurm
    dependencies (see [the example below](#orchestrating-a-multi-step-slurm-pipeline)).
    Prefer the plain Question/Answer flow when it suffices, and reach for these calls
    deliberately.

## Migrating from `subprocess.run`

Before, a `jobbergate.py` workflow method would invoke the CLI recursively:

```python
import subprocess


class JobbergateApplication(JobbergateApplicationBase):
    def mainflow(self, data=None):
        subprocess.run(
            ["jobbergate", "job-scripts", "create", "-n", "my-job-script", "--fast", "my-app"],
            capture_output=True,
            check=True,
        )
        return []
```

After, import the command and call it directly:

```python
from jobbergate_cli.subapps.job_scripts.app import create


class JobbergateApplication(JobbergateApplicationBase):
    def mainflow(self, data=None):
        result = create(
            id_or_identifier="my-app",
            name="my-job-script",
            fast=True,
            submit=False,
            download=False,
        )
        # ``result`` is a JobScriptResponse, so details are directly available
        self.jobbergate_config["created_job_script_id"] = result.job_script_id
        return []
```

### Supplying template parameters directly

On the CLI, template parameters are supplied through `--param-file`, a JSON file. When
calling `create` (or `create_locally`) as a function, the `param_dict` argument takes the
parameters directly as a dictionary -- no need to encode a JSON file just to have it
decoded again moments later. It is hidden from the CLI help (where `--param-file` is the
supported path), and its keys take precedence over `param_file` entries:

```python
result = create(
    id_or_identifier="my-app",
    name="my-job-script",
    fast=True,
    submit=False,
    download=False,
    param_dict={"partition": "debug", "nodes": 2},
)
```

### Recreating the current job script

Applications often re-invoke the very creation flow they are running in (e.g. to fan out a
batch of sibling job scripts with different parameters). Instead of repeating the command
and its selection, import `recreate`: while `create` or `create-locally` is executing the
application, it points to the same command bound to the same selection -- the same
`id_or_identifier` under `create`, or the same `application_path` under `create-locally`.
All arguments are forwarded:

```python
from jobbergate_cli.subapps.job_scripts import recreate


class JobbergateApplication(JobbergateApplicationBase):
    def mainflow(self, data=None):
        for nodes in (1, 2, 4):
            recreate(
                name=f"scaling-study-{nodes}",
                fast=True,
                submit=False,
                download=False,
                param_dict={"nodes": nodes},
            )
        return []
```

Note that `create` and `create-locally` take different arguments (`create` has extras like
`description`, `submit`, and `download`). To keep the same `recreate` call valid under
both, arguments that the underlying command does not accept -- or that would override the
original selection -- are ignored, and a warning listing them is logged so nothing is
dropped silently.

Calling `recreate` outside of a running creation -- including from any other command --
raises `Abort`. Recreation is also limited to a single level: an application may call
`recreate` several times in sequence (as above), but a run that was itself started by
`recreate` cannot call it again, which rules out unbounded recursion.


## Orchestrating a multi-step Slurm pipeline

A workflow that genuinely needs several coordinated jobs can create and submit each step
in-process, chaining them with Slurm dependencies so each step only starts after the
previous one succeeds:

```python
from jobbergate_cli.subapps.job_scripts.app import create
from jobbergate_cli.subapps.job_submissions.app import create as create_submission


class JobbergateApplication(JobbergateApplicationBase):
    def mainflow(self, data=None):
        previous_slurm_job_id = None
        for step in ("preprocess", "solve", "postprocess"):
            job_script = create(
                id_or_identifier=f"pipeline-{step}",
                name=f"my-pipeline-{step}",
                fast=True,
                submit=False,
                download=False,
                param_dict={**data, "step": step} if data is not None else None
            )
            submission = create_submission(
                job_script_id=job_script.job_script_id,
                name=f"my-pipeline-{step}",
                sbatch_arguments=(
                    [f"--dependency=afterok:{previous_slurm_job_id}"] if previous_slurm_job_id else None
                ),
            )
            if submission.slurm_job_id is None:
                submission = self.sdk.job_submissions.get_one_ensure_slurm_id(submission.job_submission_id)
            previous_slurm_job_id = submission.slurm_job_id
        return []
```

Note that `slurm_job_id` is available right away in on-site mode, where the submission runs
`sbatch` locally. In remote mode the agent performs the submission later, so the id is not
known at creation time, extra mechanisms are needed to retrieve it after the fact (e.g. by polling the submission status).

## How the active context works

When the CLI starts, its main entry point stores the `JobbergateContext` (authentication
handler, API client, and output preferences) in a `ContextVar` called the *active context*.
Commands called directly as functions resolve their context from it, so any code running
in-process within a CLI session -- including `jobbergate.py` applications -- can call the
commands with no extra setup.

A few points to keep in mind:

- **The active context is set automatically by the CLI.** Inside a running `jobbergate.py`
  application there is nothing to configure; just import the command and call it. The CLI
  leaves the context set for the lifetime of the process, which is fine for CLI runs.
- **`ContextVar` values do not propagate to threads.** If the application starts a new
  `threading.Thread`, the thread will not see the main thread's active context. Either set
  the active context inside the thread or keep the calls on the main thread.
- **Standalone embedders must activate a context themselves.** Code that runs outside of a
  CLI session (e.g. a custom script embedding Jobbergate) should activate one explicitly
  with the `active_context` context manager, which also restores the previous state on exit:

    ```python
    from jobbergate_cli.context import JobbergateContext, active_context
    from jobbergate_cli.subapps.job_scripts.app import create

    with active_context(JobbergateContext()):
        result = create(id_or_identifier="my-app", name="my-job-script", fast=True, submit=False, download=False)
    ```

- **You must pass `fast`, `submit`, and `download` explicitly.** The commands keep their
  interactive behavior, so any omitted option falls back to an interactive prompt. In a
  non-interactive environment the prompt fails outright (with an error that is *not* a
  Jobbergate `Abort`). Always pass `fast=True, submit=..., download=...` when calling the
  commands programmatically.
- **Pass all arguments as keyword arguments.** The first parameter of every command is the
  (optional) click context, so a positional call like `create("my-app")` would bind the
  value to the wrong parameter. The commands guard against this with a clear error, but
  keyword arguments avoid the problem entirely.
