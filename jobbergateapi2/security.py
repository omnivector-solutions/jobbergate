"""
Instantiates armada-security resources for auth on api endpoints using project settings.
Also provides a factory function for TokenSecurity to reduce boilerplate.
"""

from armasec import Armasec
from loguru import logger

from jobbergateapi2.config import settings

guard = Armasec(
    settings.ARMASEC_DOMAIN,
    audience=settings.ARMASEC_AUDIENCE,
    debug_logger=logger.debug if settings.ARMASEC_DEBUG else None,
)
