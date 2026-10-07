from urllib.parse import urlparse

from django.conf import settings
from django.http import JsonResponse

from .exceptions import error_body

SAFE_METHODS = {'GET', 'HEAD', 'OPTIONS'}


class VerifyOriginMiddleware:
    """
    Origin check on state-changing API requests.

    This is the primary CSRF defence for the API, not a backstop. The admin
    session cookie has to be SameSite=None in production (the web app and API
    are separate hosts, so a Lax cookie would never be sent back), which means
    the browser offers no cross-site protection of its own. Every unsafe
    request under /api/ must therefore declare one of the web app's origins.

    Requests with neither Origin nor Referer are refused as well: browsers send
    Origin on every cross-origin write, so its absence is not a real admin.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/api/') and request.method not in SAFE_METHODS:
            if not self._trusted(request):
                return JsonResponse(error_body(403, 'This request came from an unrecognised origin.'), status=403)
        return self.get_response(request)

    @staticmethod
    def _trusted(request) -> bool:
        allowed = set(settings.WEB_ORIGINS)
        origin = request.headers.get('Origin')
        if origin:
            return origin in allowed
        referer = request.headers.get('Referer')
        if referer:
            parsed = urlparse(referer)
            return f'{parsed.scheme}://{parsed.netloc}' in allowed
        return False
