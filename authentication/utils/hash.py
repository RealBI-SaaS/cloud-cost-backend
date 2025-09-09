import hashlib
import hmac


def hash_code(code: str) -> str:
    """Hash OTP code before saving (like a password)."""
    return hashlib.sha256(code.encode()).hexdigest()


def verify_code(raw_code: str, hashed_code: str) -> bool:
    """Constant-time comparison."""
    return hmac.compare_digest(hash_code(raw_code), hashed_code)
