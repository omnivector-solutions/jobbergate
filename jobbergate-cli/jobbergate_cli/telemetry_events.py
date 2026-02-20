"""Helper utilities for emitting telemetry events from CLI user interactions.

This module provides convenient decorators and context managers for tracking
user interactions like template selections, variable responses, and job submissions.

Usage:
    from jobbergate_cli.telemetry_events import track_event, track_user_interaction

    # Emit a simple event
    track_event("template_selected", template_name="my-template")

    # Track a user interaction block
    with track_user_interaction("job_submission"):
        # ... perform submission ...
        pass
"""

from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Dict, Optional

from jobbergate_cli.telemetry import get_tracer


def track_event(event_name: str, **attributes: Any) -> None:
    """Emit a telemetry event with given attributes.

    Args:
        event_name: Name of the event (e.g., "template_selected")
        **attributes: Event attributes (e.g., template_name="foo", user_id="123")

    Example:
        track_event("template_selected", template_name="abaqus", version="2021.0.0")
    """
    tracer = get_tracer()
    if not tracer:
        return

    with tracer.start_as_current_span(event_name) as span:
        for key, value in attributes.items():
            span.set_attribute(key, str(value))


@contextmanager
def track_user_interaction(interaction_name: str, **attributes: Any):
    """Context manager to track a user interaction span.

    Args:
        interaction_name: Name of the interaction (e.g., "job_submission")
        **attributes: Initial span attributes

    Example:
        with track_user_interaction("job_submission", cluster="local"):
            # ... submit job ...
            pass
    """
    tracer = get_tracer()
    if not tracer:
        yield
        return

    with tracer.start_as_current_span(interaction_name) as span:
        for key, value in attributes.items():
            span.set_attribute(key, str(value))
        yield span


def track_function(event_name: Optional[str] = None) -> Callable:
    """Decorator to track function execution as a telemetry event.

    Args:
        event_name: Optional custom name for the span. Defaults to function name.

    Example:
        @track_function("template_rendering")
        def render_template(template):
            # ... render ...
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            span_name = event_name or func.__name__
            with track_user_interaction(span_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Common event tracking functions for typical CLI workflows

def track_template_selection(template_name: str, application_name: Optional[str] = None) -> None:
    """Track when a user selects a template.

    Args:
        template_name: Name of the selected template
        application_name: Optional name of the parent application
    """
    attrs = {"template_name": template_name}
    if application_name:
        attrs["application_name"] = application_name
    track_event("cli_template_selected", **attrs)


def track_variable_response(variable_name: str, response_value: str, template_name: Optional[str] = None) -> None:
    """Track when a user responds to an interactive variable prompt.

    Args:
        variable_name: Name of the variable
        response_value: Value entered by user
        template_name: Optional name of the template being configured
    """
    attrs = {
        "variable_name": variable_name,
        "response_value": response_value,
    }
    if template_name:
        attrs["template_name"] = template_name
    track_event("cli_variable_response", **attrs)


def track_job_submission(
    template_name: str,
    cluster_name: str,
    script_count: int = 1,
) -> None:
    """Track a job submission action.

    Args:
        template_name: Name of the template used
        cluster_name: Target cluster name
        script_count: Number of scripts submitted
    """
    track_event(
        "cli_job_submission",
        template_name=template_name,
        cluster_name=cluster_name,
        script_count=script_count,
    )


def track_job_script_generation(
    template_name: str,
    generation_time_ms: float,
) -> None:
    """Track job script generation completion.

    Args:
        template_name: Name of the template used
        generation_time_ms: Time taken to generate in milliseconds
    """
    track_event(
        "cli_job_script_generated",
        template_name=template_name,
        generation_time_ms=generation_time_ms,
    )


def track_cli_command(command_name: str, subcommand: Optional[str] = None) -> None:
    """Track CLI command execution.

    Args:
        command_name: Name of the main command (e.g., "applications", "job-scripts")
        subcommand: Optional subcommand (e.g., "list", "submit")
    """
    attrs = {"command": command_name}
    if subcommand:
        attrs["subcommand"] = subcommand
    track_event("cli_command_executed", **attrs)


def track_error(error_type: str, error_message: str, command: Optional[str] = None) -> None:
    """Track error occurrences in CLI operations.

    Args:
        error_type: Type of error (e.g., "ValidationError", "APIError")
        error_message: Error message
        command: Optional command that triggered the error
    """
    attrs = {
        "error_type": error_type,
        "error_message": error_message,
    }
    if command:
        attrs["command"] = command
    track_event("cli_error", **attrs)
