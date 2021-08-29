from armasec.security import TokenSecurity
from armasec.managers import AsymmetricManager
from loguru import logger

from jobbergateapi2.config import settings

extra_kwargs = dict()
if settings.TEST_ENV:
    extra_kwargs["debug_logger"] = logger.debug

armasec_manager = AsymmetricManager(
    secret=settings.ARMASEC_SECRET,
    algorithm=settings.ARMASEC_ALGORITHM,
    client_id=settings.ARMASEC_CLIENT_ID,
    domain=settings.ARMASEC_DOMAIN,
    audience=settings.ARMASEC_AUDIENCE,
    **extra_kwargs,
)


def armasec_factory(*scopes):
    return TokenSecurity(armasec_manager, scopes=scopes if scopes else None, debug=settings.TEST_ENV)


armasec_authenticated = armasec_factory()
