"""
Admin session: a signed JWT in an httpOnly cookie.

The Next.js app never decodes the token. Its server components forward the
cookie to /api/auth/me, so this module is the only place a session is judged.
The user (and role) is re-read from the database on every request, so revoking
access takes effect on the next request, not when the token expires.
"""
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import BasePermission
from rest_framework.views import APIView

from apps.common.exceptions import ApiError

from .models import AdminUser

ALGORITHM = 'HS256'


def sign_token(user: AdminUser) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        'sub': str(user.id),
        'role': user.legacy_role,
        'iat': now,
        'exp': now + timedelta(days=settings.JWT_EXPIRES_DAYS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def _cookie_options() -> dict:
    """
    In development the web app (localhost:3001) and API (localhost:8001) are
    same-site, so Lax works over plain HTTP. In production they are separate
    hosts, and only SameSite=None (which requires Secure) is sent back
    cross-site. The CSRF protection that gives up is replaced by
    VerifyOriginMiddleware.
    """
    production = settings.IS_PRODUCTION
    options = {'httponly': True, 'samesite': 'None' if production else 'Lax', 'secure': production, 'path': '/'}
    if settings.AUTH_COOKIE_DOMAIN:
        options['domain'] = settings.AUTH_COOKIE_DOMAIN
    return options


def set_auth_cookie(response, token: str) -> None:
    response.set_cookie(
        settings.AUTH_COOKIE_NAME, token, max_age=settings.JWT_EXPIRES_DAYS * 24 * 3600, **_cookie_options()
    )


def clear_auth_cookie(response) -> None:
    # Must mirror set_auth_cookie's attributes, or the browser treats it as a
    # different cookie and logout silently does nothing.
    options = _cookie_options()
    response.delete_cookie(
        settings.AUTH_COOKIE_NAME, path=options['path'], domain=options.get('domain'), samesite=options['samesite']
    )


class CookieJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        token = request.COOKIES.get(settings.AUTH_COOKIE_NAME)
        if not token:
            return None
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        except jwt.PyJWTError:
            request._clear_auth_cookie = True
            raise ApiError.unauthorized('Your session has expired. Please sign in again.')

        user = (
            AdminUser.objects.select_related('role')
            .filter(pk=payload.get('sub'), is_active=True)
            .first()
            if _is_uuid(payload.get('sub'))
            else None
        )
        if user is None:
            request._clear_auth_cookie = True
            raise ApiError.unauthorized('That account no longer exists.')
        return (user, token)

    def authenticate_header(self, request):
        # Makes DRF answer 401 rather than 403 for unauthenticated requests.
        return 'Cookie'


def _is_uuid(value) -> bool:
    import uuid

    try:
        uuid.UUID(str(value))
        return True
    except ValueError:
        return False


class HasDashboardPermission(BasePermission):
    """
    Reads `required_permissions` from the view: a dict of HTTP method ->
    permission string (or tuple of them), or a single string for all methods.
    `full_admin_methods` lists methods reserved for the coarse 'admin' role.
    """

    def has_permission(self, request, view):
        user = request.user
        if user is None:
            raise ApiError.unauthorized()

        required = getattr(view, 'required_permissions', None)
        if isinstance(required, dict):
            required = required.get(request.method)
        if required:
            perms = (required,) if isinstance(required, str) else tuple(required)
            if not user.has_dashboard_permission(*perms):
                raise ApiError.forbidden('Your role does not include permission to do that.')
        return True


class PublicView(APIView):
    authentication_classes: list = []
    permission_classes: list = []


class AdminView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [HasDashboardPermission]
    required_permissions: dict | str | None = None

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        if getattr(request, '_clear_auth_cookie', False) or getattr(request._request, '_clear_auth_cookie', False):
            clear_auth_cookie(response)
        return response


def require(request, *permissions: str) -> None:
    """Imperative check for permissions that depend on the payload (e.g. publishing)."""
    if not request.user.has_dashboard_permission(*permissions):
        raise ApiError.forbidden('Your role does not include permission to do that.')


def client_ip(request) -> str | None:
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()[:64]
    return (request.META.get('REMOTE_ADDR') or '')[:64] or None
