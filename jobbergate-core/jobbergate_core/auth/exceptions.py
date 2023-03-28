from buzz import Buzz


class AuthenticationError(Buzz):
    """
    Base exception for errors related to authentication on Jobbergate.
    """

    pass


class TokenError(AuthenticationError):
    """
    Exception for errors related to tokens on Jobbergate.
    """

    pass
