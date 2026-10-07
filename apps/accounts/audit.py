import logging

from .auth import client_ip
from .models import AuditLog

logger = logging.getLogger('api.audit')

_REDACTED = {'password', 'password_hash', 'passwordHash'}


def write_audit(request, action: str, target: dict | None = None, changes: dict | None = None) -> None:
    """
    Append to the audit log. Non-fatal on purpose: failing to record history
    must not undo or block the change the admin actually asked for.

    Never pass a password or a whole user record as `changes`; build it with
    record_changes() below.
    """
    user = getattr(request, 'user', None)
    target = target or {}
    try:
        AuditLog.objects.create(
            actor=user if user is not None else None,
            actor_email=getattr(user, 'email', None) or 'system',
            action=action,
            target_type=target.get('type'),
            target_id=target.get('id'),
            target_label=target.get('label'),
            changes=changes or {},
            ip=client_ip(request) if request is not None else None,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error('could not record %s: %s', action, exc)


def record_changes(before: dict, after: dict) -> dict:
    """{before, after} of only the fields that changed; credentials become a flag."""
    changed = {'before': {}, 'after': {}}
    for key, value in after.items():
        if key in _REDACTED:
            changed['after']['passwordChanged'] = True
            continue
        if (before or {}).get(key) != value:
            changed['before'][key] = (before or {}).get(key)
            changed['after'][key] = value
    return changed
