from armasec.security import TokenSecurity
from armasec.managers import AsymmetricManager
from armasec.managers.test import TestTokenManager
from loguru import logger

from jobbergateapi2.config import settings

if settings.TEST_ENV:
    armasec_manager = TestTokenManager(
        secret=settings.ARMASEC_SECRET,
        algorithm=settings.ARMASEC_ALGORITHM,
        issuer=settings.ARMASEC_ISSUER,
        audience=settings.ARMASEC_AUDIENCE,
        debug_logger=logger.debug,
    )
else:
    armasec_manager = AsymmetricManager(
        secret=settings.ARMASEC_SECRET,
        algorithm=settings.ARMASEC_ALGORITHM,
        client_id=settings.ARMASEC_CLIENT_ID,
        domain=settings.ARMASEC_DOMAIN,
        audience=settings.ARMASEC_AUDIENCE,
        debug_logger=logger.debug if settings.ARMASEC_DEBUG else None,
    )


def armasec_factory(*scopes):
    return TokenSecurity(armasec_manager, scopes=scopes if scopes else None, debug=settings.TEST_ENV)


armasec_authenticated = armasec_factory()
