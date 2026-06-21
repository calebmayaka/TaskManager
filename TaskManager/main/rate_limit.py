from django.core.cache import cache
from django.shortcuts import render


class RateLimitMixin:
    """
    Rate-limits POST requests by client IP using Django's cache backend.

    Subclasses may override:
        rate_limit_count  – max POST attempts allowed per window (default 10)
        rate_limit_window – sliding window size in seconds (default 3600)
    """

    rate_limit_count = 10
    rate_limit_window = 3600

    def _client_ip(self, request):
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "0.0.0.0")

    def _cache_key(self, request):
        return f"rl:{self.__class__.__name__}:{self._client_ip(request)}"

    def _is_rate_limited(self, request):
        return cache.get(self._cache_key(request), 0) >= self.rate_limit_count

    def _record_attempt(self, request):
        key = self._cache_key(request)
        try:
            cache.incr(key)
        except ValueError:
            # Key absent or expired; start a fresh window.
            cache.set(key, 1, self.rate_limit_window)

    def dispatch(self, request, *args, **kwargs):
        if request.method == "POST":
            if self._is_rate_limited(request):
                return self._rate_limit_response(request)
            self._record_attempt(request)
        return super().dispatch(request, *args, **kwargs)

    def _rate_limit_response(self, request):
        return render(
            request,
            "registration/rate_limited.html",
            {
                "window_minutes": self.rate_limit_window // 60,
                "limit": self.rate_limit_count,
            },
            status=429,
        )
