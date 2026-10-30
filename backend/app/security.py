import base64
import hashlib
import hmac
import secrets
import time
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from .config import settings

_ITERATIONS = 310_000

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"

def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt_b64, digest_b64 = stored.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(digest_b64.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False

_serializer = URLSafeTimedSerializer(settings.app_secret_key, salt="breastcare-auth")

def create_access_token(user_id: int) -> str:
    return _serializer.dumps({"sub": str(user_id), "iat": int(time.time())})

def decode_access_token(token: str) -> int | None:
    try:
        data = _serializer.loads(token, max_age=settings.token_ttl_hours * 3600)
        return int(data["sub"])
    except (BadSignature, SignatureExpired, KeyError, ValueError, TypeError):
        return None
