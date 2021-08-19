from mini_auth_token import Token, TokenManager, TokenSecurity
from jobberrgateapi2.config import settings

manager = TokenManager(
    secret_key=settings.SECRET_KEY,
    algorithm=settings.ALGORITHM,
    default_expire_in_minutes=0,
)
security = TokenSecurity(manager)
