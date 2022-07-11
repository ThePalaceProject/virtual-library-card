from datetime import datetime, timedelta

import jwt
from django.conf import settings


class TokenTypes:
    EMAIL_VERIFICATION = "emailverification"


class Tokens:
    @staticmethod
    def generate(typ, expires_in_days=1, **data) -> str:
        """Generate a jwt token given a type and expiry in days
        Any additional data is added to the token header as-is"""
        exp = datetime.utcnow() + timedelta(days=expires_in_days)
        return jwt.encode(
            dict(type=typ, exp=exp.timestamp(), **data),
            settings.SECRET_KEY,
            algorithm="HS256",
        )

    @staticmethod
    def verify(token: str) -> str:
        """Verify a token"""
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            data = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"],
                options=dict(verify_exp=False),
            )
            raise TokenExpiredError(data=data)
        except Exception:
            data = jwt.decode(token)
            # Anything else is generic
            raise TokenDecodeError()


class TokenException(Exception):
    def __init__(self, *args: object, data=None) -> None:
        self.data = data
        super().__init__(*args)


class TokenExpiredError(TokenException):
    pass


class TokenDecodeError(TokenException):
    pass
