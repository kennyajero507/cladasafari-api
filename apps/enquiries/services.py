from django.db import transaction
from django.utils import timezone

from .models import CLOSED_STATUSES, Enquiry, EnquiryEvent, EnquiryReferenceCounter, EnquiryStatus

STATUS_LABELS = dict(EnquiryStatus.choices)


def is_closed(status: str) -> bool:
    return status in CLOSED_STATUSES


def describe_status_change(old: str, new: str) -> str:
    return f'Status changed from {STATUS_LABELS.get(old, old)} to {STATUS_LABELS.get(new, new)}'


def actor_of(request) -> dict:
    user = getattr(request, 'user', None)
    return {'actor': user, 'actor_name': (user.name or user.email) if user else None}


def log_event(enquiry, type_: str, summary: str, *, actor: dict | None = None, note=None, meta=None) -> EnquiryEvent:
    actor = actor or {}
    return EnquiryEvent.objects.create(
        enquiry=enquiry,
        type=type_,
        summary=summary[:300],
        note=note,
        meta=meta or {},
        actor=actor.get('actor'),
        actor_name=actor.get('actor_name'),
    )


def status_side_effects(status: str) -> dict:
    """What a status change implies, shared by the single and bulk paths."""
    if is_closed(status):
        # A finished enquiry should not keep surfacing in the follow-up queue.
        return {'status': status, 'closed_at': timezone.now(), 'follow_up_at': None}
    return {'status': status, 'closed_at': None}


def _claim_reference(when=None) -> str:
    """Next ENQ-YYMM-NNNN for this month, under a row lock. Call inside a transaction."""
    when = when or timezone.now()
    period = when.strftime('%y%m')
    EnquiryReferenceCounter.objects.get_or_create(period=period)
    counter = EnquiryReferenceCounter.objects.select_for_update().get(period=period)
    counter.last_seq += 1
    counter.save(update_fields=['last_seq'])
    return f'ENQ-{period}-{counter.last_seq:04d}'


def create_with_reference(**fields) -> Enquiry:
    """An enquiry is never stored without a reference, and no number is burned by a failed create."""
    # `created_at` is auto_now_add, so a backdated value (used by the seed)
    # has to be written with a second UPDATE rather than passed to create().
    created_at = fields.pop('created_at', None)
    with transaction.atomic():
        enquiry = Enquiry.objects.create(reference=_claim_reference(created_at), **fields)
        if created_at is not None:
            Enquiry.objects.filter(pk=enquiry.pk).update(created_at=created_at)
            enquiry.created_at = created_at
        return enquiry
