"""Success envelope: { "success": true, "data": ..., "meta"?: ... }."""
import math

from rest_framework.response import Response


def send(data, status: int = 200, meta: dict | None = None) -> Response:
    body = {'success': True, 'data': data}
    if meta is not None:
        body['meta'] = meta
    return Response(body, status=status)


def page_meta(page: int, limit: int, total: int) -> dict:
    return {
        'page': page,
        'limit': limit,
        'total': total,
        'totalPages': max(1, math.ceil(total / limit)),
        'hasNextPage': page * limit < total,
        'hasPrevPage': page > 1,
    }


def paginate(queryset, page: int, limit: int):
    """Returns (rows, total). `rows` is materialised so serializers can iterate twice."""
    total = queryset.count()
    start = (page - 1) * limit
    return list(queryset[start : start + limit]), total
