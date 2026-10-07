"""
Tells the Next.js app that cached data for these tags is stale.

Deliberately non-fatal: a content save must not fail because the web app is
down or restarting. Sent after the surrounding transaction commits, so the web
app never re-fetches before the change is visible.
"""
import json
import logging
import threading
import urllib.request

from django.conf import settings
from django.db import transaction

logger = logging.getLogger('api.revalidate')


def _post(tags: list[str]) -> None:
    request = urllib.request.Request(
        settings.REVALIDATE_URL,
        data=json.dumps({'tags': tags}).encode(),
        headers={'Content-Type': 'application/json', 'x-revalidate-secret': settings.REVALIDATE_SECRET},
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=4) as response:
            if response.status >= 300:
                logger.warning('web app returned %s for tags %s', response.status, tags)
    except Exception as exc:  # noqa: BLE001 - any failure is logged and ignored
        logger.warning('could not reach the web app to revalidate %s: %s', tags, exc)


def revalidate(tags) -> None:
    tags = sorted({t for t in (tags or []) if t})
    if not settings.REVALIDATE_SECRET or not tags:
        return
    # A background thread keeps the admin's save from waiting on the web app.
    transaction.on_commit(lambda: threading.Thread(target=_post, args=(tags,), daemon=True).start())
