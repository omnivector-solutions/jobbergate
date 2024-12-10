"""Core module for testing the helper functions of the job submissions app."""

from math import ceil
import pytest
from jobbergate_api.apps.job_submissions.helpers import validate_job_metric_upload_input


class TestValidateJobMetricUploadInput:
    """
    Test suite for the `validate_job_metric_upload_input` function.

    This test suite contains various test cases to validate the behavior of the
    `validate_job_metric_upload_input` function under different scenarios. The
    function is expected to validate and process input data, ensuring that the
    data conforms to the expected types and structure.

    Test Cases:
    - `test_validate_job_metric_upload_input_valid_data`: Tests the function with valid data.
    - `test_validate_job_metric_upload_input_invalid_data_type`: Tests that the function raises a ValueError for invalid data types.
    - `test_validate_job_metric_upload_input_invalid_inner_type`: Tests that the function raises a ValueError for invalid inner types.
    - `test_validate_job_metric_upload_input_invalid_length`: Tests that the function raises a ValueError when the length of any iterable in `data` does not match the length of `expected_types`.
    - `test_validate_job_metric_upload_input_exceeds_max_elements`: Tests that the function raises a ValueError when the input data exceeds the maximum number of allowed elements.
    - `test_validate_job_metric_upload_input_cast_failure`: Tests that the function raises a ValueError when data cannot be cast to the expected types.
    - `test_validate_job_metric_upload_input_cast_success`: Tests that the function successfully casts data to the expected types.
    """

    def test_validate_job_metric_upload_input_valid_data(self):
        """
        Test the validate_job_metric_upload_input function with valid data.

        This test checks if the function correctly validates and processes input data
        when provided with valid data types.

        The input data consists of a list of lists, where each inner list contains
        an integer, a string, and a float. The expected types for these values are
        (int, str, float).
        """
        data = [[1, "test", 3.5], [2, "example", 4.5]]
        expected_types = (int, str, float)
        result = validate_job_metric_upload_input(data, expected_types)
        assert result == [(1, "test", 3.5), (2, "example", 4.5)]

    def test_validate_job_metric_upload_input_invalid_data_type(self):
        """
        Test that `validate_job_metric_upload_input` raises a ValueError when provided with data of an invalid type.

        This test checks that the function correctly identifies and rejects data that is not of the expected type, i.e. list.
        """
        data = "invalid data type"
        expected_types = (int, str, float)
        with pytest.raises(ValueError, match="Decoded data must be a list."):
            validate_job_metric_upload_input(data, expected_types)

    def test_validate_job_metric_upload_input_invalid_inner_type(self):
        """
        Test that `validate_job_metric_upload_input` raises a ValueError when the input data contains an invalid inner type.

        This test checks that the function correctly identifies and raises an error when the input data is not a list of lists or tuples.

        The input data contains a mix of valid and invalid types:
        - A list with elements of types int, str, and float.
        - A string which is an invalid inner type.

        The expected types for the elements are specified as a tuple: (int, str, float).

        The test expects a ValueError to be raised with the message "Decoded data must be either a list of lists or tuples".
        """
        data = [[1, "test", 3.5], "invalid inner type"]
        expected_types = (int, str, float)
        with pytest.raises(ValueError, match="Decoded data must be either a list of lists or tuples"):
            validate_job_metric_upload_input(data, expected_types)

    def test_validate_job_metric_upload_input_invalid_length(self):
        """
        Test that `validate_job_metric_upload_input` raises a ValueError when the length of any
        iterable in `data` does not match the length of `expected_types`.

        This test case provides a `data` list containing iterables of different lengths and an
        `expected_types` tuple. It asserts that a ValueError is raised with the appropriate error message.
        """
        data = [[1, "test"], [2, "example", 4.5]]
        expected_types = (int, str, float)
        with pytest.raises(
            ValueError, match="Every iterable in `data` must match the length of `expected_types`."
        ):
            validate_job_metric_upload_input(data, expected_types)

    @pytest.mark.parametrize("num_of_elements", [3, 8, 83])
    def test_validate_job_metric_upload_input_exceeds_max_elements(self, num_of_elements: int):
        """
        Test that the `validate_job_metric_upload_input` function raises a `ValueError`
        when the input data exceeds the maximum number of allowed elements.

        The test creates a list of lists `data` where each sublist contains three identical
        integers. The length of `data` is set to exceed the maximum allowed elements.
        The `expected_types` tuple specifies the expected types for each element in the sublists.

        The test asserts that a `ValueError` is raised with the message "The maximum number of elements
        has been exceeded." when `validate_job_metric_upload_input` is called with the `data` and
        `expected_types` arguments.

        Postgres limits the number of query params to 2**15 - 1. Considering that each
        element in the sublists will generate len(data) * len(expected_types) query params, the maximum
        number of elements is calculated as ceil((2**15 - 1) / num_of_elements).
        [Reference](https://www.postgresql.org/docs/17/protocol-message-formats.html)
        """
        data = [[i] * num_of_elements for i in range(ceil((2**15 - 1) / num_of_elements) + 1)]
        expected_types = [int] * num_of_elements
        with pytest.raises(
            ValueError,
            match=(
                "The maximum number of elements has been exceeded. " "Maximum is {}, received {}".format(
                    ceil((2**15 - 1) / num_of_elements), len(data)
                )
            ),
        ):
            validate_job_metric_upload_input(data, expected_types)

    def test_validate_job_metric_upload_input_cast_failure(self):
        """
        Test that `validate_job_metric_upload_input` raises a ValueError when data cannot be cast to the expected types.

        This test provides a list of data where one of the elements cannot be cast to the expected type (float).
        It expects the function to raise a ValueError with a specific error message.
        """
        data = [[1, "test", "not a float"]]
        expected_types = (int, str, float)
        with pytest.raises(ValueError, match="Failed to cast data to expected types."):
            validate_job_metric_upload_input(data, expected_types)

    def test_validate_job_metric_upload_input_cast_success(self):
        """
        Test that `validate_job_metric_upload_input` successfully casts data to the expected types.

        This test provides a list of data where one of the elements cannot be cast to the expected type (float).
        It expects the function to raise a ValueError with a specific error message.
        """
        data = [[1, "test", "3.5"]]
        expected_types = (int, str, float)
        result = validate_job_metric_upload_input(data, expected_types)
        assert result == [(1, "test", 3.5)]
