from armasec import TokenManager, TokenSecurity
from loguru import logger

from jobbergateapi2.config import settings

extra_kwargs = dict()
if settings.TEST_ENV:
    extra_kwargs["debug_logger"] = logger.debug

armasec_manager = TokenManager(
    secret=settings.ARMASEC_SECRET,
    algorithm=settings.ARMASEC_ALGORITHM,
    issuer=settings.ARMASEC_ISSUER,
    audience=settings.ARMASEC_AUDIENCE,
    **extra_kwargs,
)


def armasec_factory(*scopes):
    return TokenSecurity(armasec_manager, scopes=scopes if scopes else None, debug=settings.TEST_ENV)


armasec_authenticated = armasec_factory()
