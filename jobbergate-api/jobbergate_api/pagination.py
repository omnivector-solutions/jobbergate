"""
Pagination feature for all endpoints.
"""


class Pagination:
    """
    Basic pagination class.
    """

    def __init__(self, limit: int = 10, skip: int = 0):
        """
        Pagination constructor using default limit and skip offset.
        """
        self.limit = limit
        self.skip = skip

    def __str__(self):
        return f"limit: {self.limit}, skip: {self.skip}"
