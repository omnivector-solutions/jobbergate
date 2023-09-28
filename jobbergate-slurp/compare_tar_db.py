import json
from pathlib import Path
from loguru import logger
import difflib
from datetime import datetime

json_path = Path("next-gen-applications.json")
with json_path.open() as f:
    data = json.load(f)

job_templates = {i["id"]: i for i in data["items"]}
del data

legacy_applications = sorted([i for i in Path.cwd().glob("*") if i.is_dir() and i.name.isdigit()], key=lambda x: int(x.name))

ids_with_problems = set()

raw_line = "{id},{identifier},{problem},\n"

files = ("jobbergate.yaml", "jobbergate.py")

with open("report.md", "w") as f, open("report.csv", "w") as csv:
    for app in legacy_applications:
        id = int(app.name)

        if id not in job_templates:
            logger.warning(f"Application {id} not found in next-gen-applications.json")
            continue

        last_update = job_templates[id]["updated_at"]

        last_update_datetime = datetime.strptime(last_update, "%Y-%m-%dT%H:%M:%S.%f")

        if last_update_datetime > datetime(2023, 9, 14, 23):
            logger.warning(f"Application {id} was updated recently: {last_update_datetime}")
            continue

        problem = False
        for file in files:
            tar = (app / file).read_text()
            db = (app / ("db_" + file)).read_text()
            if tar == db:
                continue
            problem = True
            result = difflib.unified_diff(
                tar.splitlines(keepends=True),
                db.splitlines(keepends=True),
                fromfile="tarball",
                tofile="database",
            )
            
            f.write(f"## Application {id} - {file}\n\n")

            f.write("```diff\n")
            f.write("".join(result) + "\n")
            f.write("```\n\n")

        if problem:
            ids_with_problems.add(id)
        csv.write(raw_line.format(id=id, identifier=job_templates[id]["identifier"], problem=problem))

logger.info(f"Found {len(ids_with_problems)} applications with problems: {sorted(list(ids_with_problems))}")