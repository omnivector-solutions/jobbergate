import ast
import importlib
import json
import pathlib
import tempfile
import typing
from typing import Dict, Any, Tuple, cast

import yaml

from jobbergate_cli.exceptions import Abort
from jobbergate_cli.constants import (
    JOBBERGATE_APPLICATION_MODULE_FILE_NAME,
    JOBBERGATE_APPLICATION_CONFIG_FILE_NAME,
)


def validate_parameter_file(parameter_path: pathlib.Path) -> Dict[str, Any]:
    """
    Validate parameter file at the supplied path and returns the parsed dict.

    Confirms:
        parameter_path exists
        parameter_path is a valid json file
    """
    data = None
    with Abort.check_expressions(
        f"The parameter file at {parameter_path} was invalid",
        raise_kwargs=dict(
            subject="INVALID PARAMETER FILE",
            log_message=f"Parameter file located at {parameter_path} failed validation",
        ),
    ) as checker:
        checker(
            parameter_path.exists(),
            f"Parameter file {parameter_path} does not exist",
        )

        try:
            data = json.loads(parameter_path.read_text())
            is_valid_json = True
        except Exception:
            is_valid_json = False
        checker(is_valid_json, f"The parameter file at {parameter_path} is not valid JSON")

    # Make static type checkers happy
    assert data is not None
    return data


def validate_application_data(app_data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    with Abort.check_expressions(
        f"The application files fetched from the API were invalid",
        raise_kwargs=dict(
            subject="INVALID APPLICATION FILES",
            log_message=f"Application files retrieved from the API were invalid",
        ),
    ) as checker:
        app_module = app_data.get(JOBBERGATE_APPLICATION_MODULE_FILE_NAME)
        checker(
            app_module is not None,
            f"Application data does not contain {JOBBERGATE_APPLICATION_MODULE_FILE_NAME}",
        )
        if app_module is not None:
            try:
                ast.parse(app_module)
                is_valid_python = True
            except Exception:
                is_valid_python = False
            checker(is_valid_python, f"The application module from the API is not valid python code")

        app_config = app_data[JOBBERGATE_APPLICATION_CONFIG_FILE_NAME]
        checker(
            app_config is not None,
            f"Application data does not contain {JOBBERGATE_APPLICATION_CONFIG_FILE_NAME}",
        )
        if app_config is not None:
            try:
                app_config = yaml.safe_load(app_config)
                is_valid_yaml = True
            except Exception:
                is_valid_yaml = False
            checker(is_valid_yaml, f"The application config from the API is not valid YAML")

    # Make static type checkers happy
    app_module = cast(str, app_module)
    app_config = cast(Dict[str, Any], app_config)

    return (app_module, app_config)


def import_from_text(app_module: str):
    with tempfile.NamedTemporaryFile() as temp_module:
        temp_path = pathlib.Path(temp_module.name)
        temp_path.write_text(app_module)


        spec = importlib.util.spec_from_file_location("JobbergateApplication", temp_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


def execute_application(app_module: str, app_config: Dict[str, Any], supplied_params: Dict[str, Any]):
    """
    Execute the jobbergate application python module.

    This function is almost directly copied from ``jobbergate_api_wrapper``. It is untested and should be re-written.
    """
    module = import_from_text(app_module)
    application = module.JobbergateApplication(app_config)

    # Add all parameters from parameter file
    app_config["jobbergate_config"].update(supplied_params)

    # Begin question assembly, starting in "mainflow" method
    app_config["jobbergate_config"]["nextworkflow"] = "mainflow"

    while "nextworkflow" in app_config["jobbergate_config"]:
        method_to_call = getattr(
            application, app_config["jobbergate_config"].pop("nextworkflow")
        )  # Use and remove from the dict

        try:
            workflow_questions = method_to_call(data=app_config["jobbergate_config"])
        except NotImplementedError:
            response = self.error_handle(
                error="Abstract method not implemented",
                solution=f"Please implement {method_to_call.__name__} in your class.",
            )
            return response

        questions = []
        auto_answers = {}

        while workflow_questions:
            field = workflow_questions.pop(0)
            # Use pre-defined answer or ask user
            if field.variablename in supplied_params.keys():
                pass  # No further action needed, case kept here to visualize priority
            elif fast and field.default is not None:
                print(f"Default value used: {field.variablename}={field.default}")
                auto_answers[field.variablename] = field.default
            else:
                # Prepare question for user
                question = self.assemble_questions(field)
                if isinstance(question, list):
                    questions.extend(question)
                else:
                    questions.append(question)

        workflow_answers = inquirer.prompt(questions, raise_keyboard_interrupt=True)
        workflow_answers.update(auto_answers)
        app_config["jobbergate_config"].update(workflow_answers)

    data["app_config"] = json.dumps(app_config)

    # Possibly overwrite script name
    job_script_name_from_param = app_config["jobbergate_config"].get("job_script_name")
    if job_script_name_from_param:
        data["job_script_name"] = job_script_name_from_param

    if sbatch_params:
        for i, param in enumerate(sbatch_params):
            data["sbatch_params_" + str(i)] = param
        data["sbatch_params_len"] = len(sbatch_params)
