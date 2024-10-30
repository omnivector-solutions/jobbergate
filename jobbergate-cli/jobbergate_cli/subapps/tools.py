"""
Tools for the subapps.
"""

from typing import TypeVar

from click import UsageError


def resolve_application_selection(
    id_or_identifier: int | str | None = None, id: int | None = None, identifier: str | None = None, prefix: str = ""
) -> int | str:
    """
    Resolve the application selection parameters.
    """
    if isinstance(id_or_identifier, str) and id_or_identifier.isdigit():
        id_or_identifier = int(id_or_identifier)

    valid_args = [i for i in (id_or_identifier, id, identifier) if i is not None]
    counter = len(valid_args)

    if counter != 1:
        prefix_underline = prefix.replace("-", "_") + "_" if prefix else ""
        prefix_dash = prefix_underline.replace("_", "-")
        raise UsageError(
            (
                f"You must supply one and only one selection value "
                f"(positional {prefix_underline}id_or_identifier, "
                f"--{prefix_dash}id, or --{prefix_dash}identifier)"
            )
        )

    return valid_args[0]


SelectionType = TypeVar("SelectionType")


def resolve_selection(*args: SelectionType | None, option_name: str = "id") -> SelectionType:
    """
    Resolve the multiple optional selection parameters to ensure one value is indeed selected.
    """
    valid_args = [i for i in args if i is not None]
    counter = len(valid_args)

    if counter != 1:
        raise UsageError(
            (
                f"You must supply one and only one selection value "
                f"(positional {option_name} or --{option_name.replace('_', '-')})"
            )
        )

    return valid_args[0]
