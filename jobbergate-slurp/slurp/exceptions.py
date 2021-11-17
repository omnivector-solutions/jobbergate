"""
Provides custom exceptions for the slurp applicaiton
"""
from buzz import Buzz


class SlurpException(Buzz):
    """
    Base exception for the slurp application.

    Inherits from Buzz to enable conveneince functions like ``require_condition()`` and
    ``handle_errors()``
    """
