"""Provide a method for coercing id_or_identifier to a string or int."""


def coerce_id_or_identifier(id_or_identifier: str) -> int | str:
    """
    Determine whether the id_or_identifier should be a string or an integer.

    This is necessary because FastAPI no longer automatically converts path parameters to integers
    automatically if they may also be string values.
    """
    try:
        return int(id_or_identifier)
    except ValueError:
        return id_or_identifier
