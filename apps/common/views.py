import time

from django.db import connection
from django.http import JsonResponse

from .exceptions import error_body

_STARTED = time.time()


def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        database = 'connected'
    except Exception:  # noqa: BLE001
        database = 'disconnected'
    return JsonResponse(
        {
            'success': True,
            'data': {
                'status': 'ok',
                'uptimeSeconds': round(time.time() - _STARTED),
                'database': database,
                'engine': connection.vendor,
            },
        }
    )


def json_not_found(request, exception=None):
    return JsonResponse(error_body(404, f'No route matches {request.method} {request.path}'), status=404)


def json_server_error(request):
    return JsonResponse(error_body(500, 'Something went wrong.'), status=500)
