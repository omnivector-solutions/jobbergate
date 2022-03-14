from random import random, randint

import typer

from fake_sbatch.config import settings


app = typer.Typer()


@app.command(context_settings=dict(allow_extra_args=True, ignore_unknown_options=True))
def submit():
    roll = random()
    if roll < settings.FAKE_SBATCH_FAIL_PCT:
        typer.echo(f"Fake sbatch failed ({roll=} <= {settings.FAKE_SBATCH_FAIL_PCT})")
        raise typer.Exit(code=1)

    fake_slurm_job_id = randint(settings.FAKE_SBATCH_MIN_JOB_ID, settings.FAKE_SBATCH_MAX_JOB_ID)
    typer.echo(f"fake-sbatch: Submitted batch job {fake_slurm_job_id}")


if __name__ == '__main__':
    app()
