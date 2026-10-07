"""
Error envelope shared by every endpoint:

    { "success": false, "error": { "message", "code", "details"? } }

The web app reads `error.message` for banners and `error.details` (a flat
{field: message} map) to highlight form fields, so every failure path, from
validation to a unique-constraint race, is reduced to that shape here.
"""
import logging

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.http import Http404
from rest_framework import exceptions as drf
from rest_framework.response import Response

logger = logging.getLogger('api')

_CODES = {
    400: 'BAD_REQUEST',
    401: 'UNAUTHORIZED',
    403: 'FORBIDDEN',
    404: 'NOT_FOUND',
    405: 'METHOD_NOT_ALLOWED',
    409: 'CONFLICT',
    413: 'PAYLOAD_TOO_LARGE',
    415: 'UNSUPPORTED_MEDIA_TYPE',
    422: 'VALIDATION_ERROR',
    429: 'RATE_LIMITED',
}


class ApiError(Exception):
    """An expected failure whose message is safe to show the client."""

    def __init__(self, status: int, message: str, code: str | None = None, details: dict | None = None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.code = code or _CODES.get(status, 'INTERNAL_ERROR')
        self.details = details

    @classmethod
    def bad_request(cls, message, **kw):
        return cls(400, message, **kw)

    @classmethod
    def unauthorized(cls, message='You must sign in to do that.', **kw):
        return cls(401, message, **kw)

    @classmethod
    def forbidden(cls, message='You do not have permission to do that.', **kw):
        return cls(403, message, **kw)

    @classmethod
    def not_found(cls, message='Resource not found.', **kw):
        return cls(404, message, **kw)

    @classmethod
    def conflict(cls, message, **kw):
        return cls(409, message, **kw)

    @classmethod
    def unprocessable(cls, message='Please correct the highlighted fields.', **kw):
        return cls(422, message, **kw)


def error_body(status: int, message: str, code: str | None = None, details: dict | None = None) -> dict:
    body = {'success': False, 'error': {'message': message, 'code': code or _CODES.get(status, 'INTERNAL_ERROR')}}
    if details:
        body['error']['details'] = details
    return body


def flatten_errors(detail, prefix: str = '') -> dict:
    """DRF's nested error structure -> {'itinerary.0.title': 'message'}, first message per field."""
    out: dict[str, str] = {}
    if isinstance(detail, dict):
        for key, value in detail.items():
            name = 'non_field_errors' if key == 'non_field_errors' else str(key)
            path = f'{prefix}.{name}' if prefix else name
            if name == 'non_field_errors':
                path = prefix or '_'
            for k, v in flatten_errors(value, path).items():
                out.setdefault(k, v)
    elif isinstance(detail, list):
        if detail and all(not isinstance(item, (dict, list)) for item in detail):
            out[prefix or '_'] = str(detail[0])
        else:
            for index, item in enumerate(detail):
                if item in ({}, [], None):
                    continue
                for k, v in flatten_errors(item, f'{prefix}.{index}' if prefix else str(index)).items():
                    out.setdefault(k, v)
    else:
        out[prefix or '_'] = str(detail)
    return out


def _duplicate_field(err: IntegrityError) -> str:
    """Best-effort column name for a unique violation, for the error details."""
    text = str(err).lower()
    for candidate in ('slug', 'email', 'name', 'question', 'reference', 'url'):
        if candidate in text:
            return candidate
    return 'field'


def api_exception_handler(exc, context):
    if isinstance(exc, ApiError):
        return Response(error_body(exc.status, exc.message, exc.code, exc.details), status=exc.status)

    if isinstance(exc, drf.ValidationError):
        details = flatten_errors(exc.detail)
        message = 'Please correct the highlighted fields.'
        if list(details) == ['_']:
            message = details['_']
        return Response(error_body(422, message, 'VALIDATION_ERROR', details), status=422)

    if isinstance(exc, DjangoValidationError):
        details = flatten_errors(exc.message_dict if hasattr(exc, 'error_dict') else exc.messages)
        return Response(error_body(422, 'Please correct the highlighted fields.', 'VALIDATION_ERROR', details), status=422)

    if isinstance(exc, (drf.NotAuthenticated, drf.AuthenticationFailed)):
        message = str(exc.detail) if isinstance(exc, drf.AuthenticationFailed) else 'You must sign in to do that.'
        return Response(error_body(401, message), status=401)

    if isinstance(exc, drf.PermissionDenied):
        return Response(error_body(403, str(exc.detail)), status=403)

    if isinstance(exc, drf.Throttled):
        message = 'Too many requests from this address. Please try again later.'
        return Response(error_body(429, message), status=429)

    if isinstance(exc, (Http404, drf.NotFound, ObjectDoesNotExist)):
        return Response(error_body(404, 'We could not find that record.'), status=404)

    if isinstance(exc, drf.ParseError):
        return Response(error_body(400, 'The request body could not be read as JSON.'), status=400)

    if isinstance(exc, drf.UnsupportedMediaType):
        return Response(error_body(415, 'That content type is not supported.'), status=415)

    if isinstance(exc, drf.MethodNotAllowed):
        return Response(error_body(405, 'That method is not allowed here.'), status=405)

    if isinstance(exc, IntegrityError):
        field = _duplicate_field(exc)
        if 'unique' in str(exc).lower() or 'duplicate' in str(exc).lower():
            return Response(
                error_body(409, f'An item with that {field} already exists.', 'DUPLICATE_KEY', {field: 'Already in use.'}),
                status=409,
            )
        return Response(
            error_body(400, 'That record refers to something that no longer exists.', 'INVALID_REFERENCE'),
            status=400,
        )

    if isinstance(exc, drf.APIException):
        return Response(error_body(exc.status_code, str(exc.detail)), status=exc.status_code)

    logger.exception('Unhandled API error', exc_info=exc)
    body = error_body(500, 'Something went wrong.', 'INTERNAL_ERROR')
    if settings.DEBUG:
        body['error']['debug'] = repr(exc)
    return Response(body, status=500)
