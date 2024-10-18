"""
Tools for the subapps.
"""

from jobbergate_cli.exceptions import Abort


def sanitize_application_selection(
    id_or_identifier: int | str | None = None, id: int | None = None, identifier: str | None = None, prefix: str = ""
) -> int | str:
    """
    Sanitize the application selection parameters.
    """
    counter = sum((0 if i is None else 1 for i in (id_or_identifier, id, identifier)))
    prefix_underline = prefix.replace("-", "_") + "_"
    prefix_dash = prefix.replace("_", "-") + "-"

    if counter != 1:
        raise Abort(
            (
                f"You must supply one and only one selection value "
                f"(positional [yellow]{prefix_underline}id_or_identifier[/yellow], "
                f"[yellow]--{prefix_dash}id[/yellow], or [yellow]{prefix_dash}identifier[/yellow]), got {counter}"
            ),
            subject="Invalid Selection",
            support=False,
        )
    if isinstance(id_or_identifier, str) and id_or_identifier.isdigit():
        id_or_identifier = int(id_or_identifier)

    return id_or_identifier or id or identifier  # type: ignore


def sanitize_id_selection(*args: int | None, option_name: str = "id") -> int:
    """
    Sanitize the id selection parameters.
    """
    valid_args = [i for i in args if i is not None]
    counter = len(valid_args)

    if counter != 1:
        raise Abort(
            (
                "You must supply one and only one selection value "
                f"(positional [yellow]{option_name}[/yellow] or "
                f"[yellow]--{option_name.replace('_', '-')}[/yellow]), got {counter}",
            ),
            subject="Invalid Selection",
            support=False,
        )

    return valid_args[0]
