"""
Since we are implementing a data retention policy for job entries in Jobbergate, we want to create a one-time backup to not lose the history.

This one-time backup should be scrubbed of user data (email).
"""

from pathlib import Path
from jobbergate_cli.context import JobbergateContext
from jobbergate_cli.subapps.applications.tools import save_application_files
from jobbergate_cli.subapps.job_scripts.tools import download_job_script_files

context = JobbergateContext()
BASE_PATH = Path("ASP-6876")
PAGE_SIZE= 20

def pull_applications():
    entry_path = BASE_PATH / "job_templates"
    entry_path.mkdir(parents=True, exist_ok=True)
    page = 1
    while True:
        page_path = entry_path / "pages" / f"{page}.json"
        page_path.parent.mkdir(parents=True, exist_ok=True)

        if page_path.is_file():
            page += 1
            continue

        jobs = context.sdk.job_templates.get_list(
            page=page,
            include_null_identifier=True,
            include_archived=True,
            sort_ascending=True,
            user_only=False,
            sort_field="id",
            size=PAGE_SIZE,
        )
        if not jobs.items:
            break
        for j in jobs.items:
            details_folder = entry_path / str(j.id)
            details_path = details_folder / "details.json"

            if details_path.is_file():
                continue

            details_folder.mkdir(parents=True, exist_ok=True)
            details = context.sdk.job_templates.get_one(
                j.id,
            )
            save_application_files(context, details, details_folder)
            details_path.write_text(details.model_dump_json(indent=4, exclude=["owner_email"]))
        page += 1
        if len(jobs.items) == PAGE_SIZE:
            page_path.write_text(jobs.model_dump_json(indent=4))

def pull_job_scripts():
    entry_path = BASE_PATH / "job_scripts"
    entry_path.mkdir(parents=True, exist_ok=True)
    page = 1
    while True:
        page_path = entry_path / "pages" / f"{page}.json"
        page_path.parent.mkdir(parents=True, exist_ok=True)

        if page_path.is_file():
            page += 1
            continue

        jobs = context.sdk.job_scripts.get_list(
            page=page,
            sort_ascending=True,
            user_only=False,
            sort_field="id",
            size=PAGE_SIZE,
            include_archived=True,
        )
        if not jobs.items:
            break
        for j in jobs.items:
            details_folder = entry_path / str(j.id)
            details_path = details_folder / "details.json"

            if details_path.is_file():
                continue

            details_folder.mkdir(parents=True, exist_ok=True)
            details = context.sdk.job_scripts.get_one(
                j.id,
            )
            download_job_script_files(details, context, details_folder)
            details_path.write_text(details.model_dump_json(indent=4, exclude=["owner_email"]))
        page += 1
        if len(jobs.items) == PAGE_SIZE:
            page_path.write_text(jobs.model_dump_json(indent=4))

def pull_job_submissions():
    entry_path = BASE_PATH / "job_submissions"
    entry_path.mkdir(parents=True, exist_ok=True)
    page = 1
    while True:
        page_path = entry_path / "pages" / f"{page}.json"
        page_path.parent.mkdir(parents=True, exist_ok=True)

        if page_path.is_file():
            page += 1
            continue

        jobs = context.sdk.job_submissions.get_list(
            page=page,
            sort_ascending=True,
            user_only=False,
            sort_field="id",
            size=PAGE_SIZE,
            include_archived=True,
        )
        if not jobs.items:
            break
        for j in jobs.items:
            details_folder = entry_path / str(j.id)
            details_path = details_folder / "details.json"

            if details_path.is_file():
                continue

            details_folder.mkdir(parents=True, exist_ok=True)
            details = context.sdk.job_submissions.get_one(
                j.id,
            )
            details_path.write_text(details.model_dump_json(indent=4, exclude=["owner_email"]))
        page += 1
        if len(jobs.items) == PAGE_SIZE:
            page_path.write_text(jobs.model_dump_json(indent=4))

if __name__ == "__main__":
    pull_applications()
    pull_job_scripts()
    pull_job_submissions()
