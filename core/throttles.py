# throttles.py
from rest_framework.throttling import SimpleRateThrottle


class OTPRequestThrottle(SimpleRateThrottle):
    scope = "otp_request"

    def get_cache_key(self, request, view):
        # Throttle by email if provided, else by IP
        email = request.data.get("email")
        if email:
            return self.cache_format % {"scope": self.scope, "ident": email.lower()}
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class OTPVerifyThrottle(SimpleRateThrottle):
    scope = "otp_verify"

    def get_cache_key(self, request, view):
        email = request.data.get("email")
        if email:
            return self.cache_format % {"scope": self.scope, "ident": email.lower()}
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }
