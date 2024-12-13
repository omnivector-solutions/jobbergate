"""Core helper functions for job submissions."""

from collections.abc import Iterable
from math import ceil
from typing import Any, Type

from loguru import logger


def _force_cast(object: Any, expected_type: Type[Any]) -> Any:
    """Forcefully cast a value to the expected type.

    Args:
        value (Any): The value to be cast.
        expected_type (Type[Any]): The type to cast the value to.

    Returns:
        Any: The value cast to the expected type.
    """
    return expected_type(object)


def validate_job_metric_upload_input(
    data: Any, expected_types: tuple[Type[Any], ...]
) -> Iterable[tuple[Any]]:
    """Validate if the input data of job metric upload is correct once decoded.

    It will brute force apply the expected types to the data and raise an error in case it fails.

    Args:
        data (Iterable[list[Any] | tuple[Any]]): The decoded data, which should be a list of lists or tuples,
            where each inner list or tuple contains the data for a single job metric upload.
        expected_types (tuple[Type[Any], ...]): A tuple of types that each element in the inner lists or tuples
            should match.

    Returns:
        Iterable[list[Any] | tuple[Any]]: The validated data.
    """
    if not isinstance(data, list):
        raise ValueError("Decoded data must be a list.")
    if not all(isinstance(x, (list, tuple)) for x in data):
        raise ValueError("All elements of the inner data must be a Sequence")
    if not all(len(x) == len(expected_types) for x in data):
        raise ValueError("Every iterable in `data` must match the length of `expected_types`.")
    # postgres limits the number of query params to 2**15 - 1
    # https://www.postgresql.org/docs/17/protocol-message-formats.html
    if len(expected_types) * len(data) > 2**15 - 1:
        raise ValueError(
            "The maximum number of elements has been exceeded. " "Maximum is {}, received {}".format(
                ceil((2**15 - 1) / len(expected_types)), len(data)
            )
        )
    for idx, aggregated_data in enumerate(data):
        # for each element in the inner list or tuple, force apply the expected type
        try:
            data[idx] = tuple(
                _force_cast(data, expected_types[idx]) for idx, data in enumerate(aggregated_data)
            )
        except Exception as e:
            logger.error(f"Failed to cast data to expected types: {e}")
            raise ValueError("Failed to cast data to expected types.")
    return data
