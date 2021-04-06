"""
Pagination feature for all endpoints
"""


class Pagination:
    """
    Basic pagination class
    """

    def __init__(self, q: str = None, limit: int = 10, offset: int = 0):
        """
        Pagination constructor using default limit and offset
        """
        self.q = q
        self.limit = limit
        self.offset = offset

    def __str__(self):
        return f"q: {self.q}, limit: {self.limit}, offset: {self.offset}"
