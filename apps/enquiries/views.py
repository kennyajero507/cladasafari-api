from django.db import transaction
from django.db.models import Count, F, Q
from django.utils import timezone
from rest_framework import serializers
from rest_framework.throttling import ScopedRateThrottle

from apps.accounts.auth import AdminView, PublicView
from apps.accounts.models import AdminUser
from apps.catalog.models import Tour
from apps.common.exceptions import ApiError
from apps.common.responses import page_meta, paginate, send
from apps.common.validation import BulkIds, PaginationQuery, SearchField, query_dict, validate

from .models import OPEN_STATUSES, Enquiry, EnquiryEvent, EnquiryStatus, EnquiryType
from .services import (
    STATUS_LABELS,
    actor_of,
    create_with_reference,
    describe_status_change,
    is_closed,
    log_event,
    status_side_effects,
)

# What the contact form offers under "I'm interested in".
INTERESTS = [
    'Local Packages',
    'Getaways',
    'International Packages',
    'Safari Packages',
    'Air Ticketing',
    'Tailor-made Trip',
]

# ---------------------------------------------------------------------------
# Shapes
# ---------------------------------------------------------------------------


def _person(user: AdminUser | None) -> dict | None:
    if user is None:
        return None
    return {'id': str(user.id), '_id': str(user.id), 'name': user.name, 'email': user.email}


def event_shape(e: EnquiryEvent) -> dict:
    return {
        'id': str(e.id),
        '_id': str(e.id),
        'type': e.type,
        'actorName': e.actor_name,
        'summary': e.summary,
        'note': e.note,
        'meta': e.meta,
        'createdAt': e.created_at,
    }


def enquiry_shape(e: Enquiry, with_events: bool = False) -> dict:
    guests = e.guests or None
    shape = {
        'id': str(e.id),
        '_id': str(e.id),
        'reference': e.reference,
        'type': e.type,
        'name': e.name,
        'email': e.email,
        'phone': e.phone or None,
        'interest': e.interest or None,
        'budget': e.budget,
        'budgetCurrency': e.budget_currency or None,
        'message': e.message or None,
        'tour': {'_id': str(e.tour.id), 'id': str(e.tour.id), 'title': e.tour.title, 'slug': e.tour.slug} if e.tour_id else None,
        'tourTitle': e.tour_title or None,
        'travelDate': e.travel_date,
        'guests': guests,
        'totalGuests': (
            sum(int(guests.get(k, 0)) for k in ('adults', 'children', 'infants')) if e.type == 'booking' and guests else None
        ),
        'status': e.status,
        'adminNotes': e.admin_notes or None,
        'source': e.source,
        'isSample': e.is_sample,
        'assignee': _person(e.assignee),
        'assignedAt': e.assigned_at,
        'lastContactedAt': e.last_contacted_at,
        'followUpAt': e.follow_up_at,
        'closedAt': e.closed_at,
        'isOverdue': bool(e.follow_up_at and e.follow_up_at < timezone.now() and not is_closed(e.status)),
        'createdAt': e.created_at,
        'updatedAt': e.updated_at,
    }
    if with_events:
        shape['events'] = [event_shape(ev) for ev in e.events.all()[:100]]
    return shape


def _load(id, *, events: bool = False) -> Enquiry:
    qs = Enquiry.objects.select_related('tour', 'assignee')
    if events:
        qs = qs.prefetch_related('events')
    enquiry = qs.filter(pk=id).first()
    if enquiry is None:
        raise ApiError.not_found('That enquiry no longer exists.')
    return enquiry


# ---------------------------------------------------------------------------
# Public submission
# ---------------------------------------------------------------------------


class GuestsSchema(serializers.Serializer):
    adults = serializers.IntegerField(min_value=1, max_value=50, default=1)
    children = serializers.IntegerField(min_value=0, max_value=50, default=0)
    infants = serializers.IntegerField(min_value=0, max_value=50, default=0)


class EnquiryBase(serializers.Serializer):
    name = serializers.CharField(min_length=2, max_length=120, error_messages={'min_length': 'Please tell us your name.', 'blank': 'Please tell us your name.'})
    email = serializers.EmailField(error_messages={'invalid': 'Enter a valid email address.', 'blank': 'Enter a valid email address.'})
    phone = serializers.CharField(max_length=40, required=False, allow_blank=True, allow_null=True)


class ContactEnquiry(EnquiryBase):
    interest = serializers.ChoiceField(choices=INTERESTS, required=False, allow_blank=True, allow_null=True)
    budget = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False, allow_null=True)
    budgetCurrency = serializers.ChoiceField(choices=['KES', 'USD'], required=False, allow_null=True)
    message = serializers.CharField(
        min_length=10,
        max_length=4000,
        error_messages={'min_length': 'Tell us a little about your trip.', 'blank': 'Tell us a little about your trip.'},
    )


class BookingEnquiry(EnquiryBase):
    tour = serializers.UUIDField(required=False, allow_null=True)
    tourTitle = serializers.CharField(max_length=140, required=False, allow_blank=True)
    travelDate = serializers.DateField(required=False, allow_null=True)
    guests = GuestsSchema(required=False)
    message = serializers.CharField(max_length=4000, required=False, allow_blank=True, allow_null=True)

    def validate_travelDate(self, value):
        if value and value < timezone.localdate():
            raise serializers.ValidationError('Choose a date in the future.')
        return value


class SubmitEnquiryView(PublicView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'enquiries'

    def post(self, request):
        kind = request.data.get('type') if isinstance(request.data, dict) else None
        if kind not in EnquiryType.values:
            raise ApiError.unprocessable(details={'type': 'Enquiry type must be "contact" or "booking".'})

        if kind == EnquiryType.CONTACT:
            body = validate(ContactEnquiry, request.data)
            fields = {
                'interest': body.get('interest') or '',
                'budget': body.get('budget'),
                'budget_currency': (body.get('budgetCurrency') or ('KES' if body.get('budget') else '')),
                'message': body['message'],
            }
            summary = 'Contact enquiry received'
        else:
            body = validate(BookingEnquiry, request.data)
            tour = Tour.objects.filter(pk=body['tour']).first() if body.get('tour') else None
            fields = {
                'tour': tour,
                'tour_title': (tour.title if tour else body.get('tourTitle') or ''),
                'travel_date': body.get('travelDate'),
                'guests': dict(body.get('guests') or {'adults': 1, 'children': 0, 'infants': 0}),
                'message': body.get('message') or '',
            }
            summary = f"Booking enquiry received for {fields['tour_title'] or 'a tour'}"

        enquiry = create_with_reference(
            type=kind,
            name=body['name'].strip(),
            email=body['email'].strip().lower(),
            phone=(body.get('phone') or '').strip(),
            source='website',
            **fields,
        )
        # Written after the row rather than with it: a customer's submission
        # must never fail because the timeline did.
        try:
            log_event(enquiry, 'created', summary, meta={'source': enquiry.source})
        except Exception:  # noqa: BLE001
            pass

        # Only what the sender needs; never the admin fields.
        return send(
            {'id': str(enquiry.id), '_id': str(enquiry.id), 'reference': enquiry.reference, 'type': enquiry.type,
             'createdAt': enquiry.created_at},
            status=201,
        )


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

ENQUIRY_SORTS = {
    'newest': ['-created_at'],
    'oldest': ['created_at'],
    'name-asc': ['name'],
    # Soonest follow-up first; rows with none sink to the bottom.
    'follow-up': [F('follow_up_at').asc(nulls_last=True)],
    # Triage default: whatever has waited longest without an owner.
    'oldest-open': [F('assignee').asc(nulls_first=True), 'created_at'],
}


def _status_list(value):
    items = [s.strip() for s in (value or '').split(',') if s.strip()]
    if any(s not in EnquiryStatus.values for s in items):
        raise serializers.ValidationError('Unknown enquiry status.')
    return items


class EnquiryQuery(PaginationQuery):
    status = serializers.CharField(required=False, allow_blank=True)
    type = serializers.ChoiceField(choices=EnquiryType.values, required=False)
    assignee = serializers.CharField(required=False)
    overdue = serializers.ChoiceField(choices=['true', 'false'], required=False)
    q = SearchField()
    sort = serializers.ChoiceField(choices=list(ENQUIRY_SORTS), required=False)

    def validate_status(self, value):
        return _status_list(value)

    def validate_assignee(self, value):
        if value in ('me', 'unassigned'):
            return value
        try:
            import uuid

            return str(uuid.UUID(value))
        except ValueError:
            raise serializers.ValidationError('That is not a valid id.')


class EnquiryListView(AdminView):
    required_permissions = 'enquiries.view'

    def get(self, request):
        q = validate(EnquiryQuery, query_dict(request))
        qs = Enquiry.objects.select_related('tour', 'assignee')
        statuses = q.get('status') or []
        if statuses:
            qs = qs.filter(status__in=statuses)
        if q.get('type'):
            qs = qs.filter(type=q['type'])
        assignee = q.get('assignee')
        if assignee == 'unassigned':
            qs = qs.filter(assignee__isnull=True)
        elif assignee == 'me':
            qs = qs.filter(assignee=request.user)
        elif assignee:
            qs = qs.filter(assignee_id=assignee)
        if q.get('overdue') == 'true':
            qs = qs.filter(follow_up_at__lt=timezone.now())
            if not statuses:
                qs = qs.filter(status__in=OPEN_STATUSES)
        if q.get('q'):
            term = q['q']
            qs = qs.filter(
                Q(reference__icontains=term) | Q(name__icontains=term) | Q(email__icontains=term) | Q(message__icontains=term)
            )
        qs = qs.order_by(*ENQUIRY_SORTS.get(q.get('sort'), ENQUIRY_SORTS['newest']))
        rows, total = paginate(qs, q['page'], q['limit'])

        # Board counts span the whole pipeline, not the filtered view: they are
        # the tabs you filter *with*.
        counts = dict(Enquiry.objects.values('status').annotate(n=Count('id')).values_list('status', 'n'))
        meta = {
            **page_meta(q['page'], q['limit'], total),
            'statusCounts': counts,
            'unassignedCount': Enquiry.objects.filter(assignee__isnull=True, status__in=OPEN_STATUSES).count(),
            'overdueCount': Enquiry.objects.filter(follow_up_at__lt=timezone.now(), status__in=OPEN_STATUSES).count(),
        }
        return send([enquiry_shape(e) for e in rows], meta=meta)


class AssignableStaffView(AdminView):
    """Everyone whose role can work enquiries; names only, no staff directory."""

    required_permissions = 'enquiries.view'

    def get(self, request):
        people = [
            _person(u)
            for u in AdminUser.objects.select_related('role').filter(is_active=True).order_by('name')
            if 'enquiries.edit' in u.dashboard_permissions
        ]
        return send(people)


class EnquiryUpdateBody(serializers.Serializer):
    # Status and assignment are deliberately absent: both have endpoints that
    # write to the timeline, and a general PATCH would make that easy to bypass.
    adminNotes = serializers.CharField(max_length=4000, required=False, allow_blank=True)
    followUpAt = serializers.DateTimeField(required=False, allow_null=True)


class EnquiryDetailView(AdminView):
    required_permissions = {'GET': 'enquiries.view', 'PATCH': 'enquiries.edit', 'DELETE': 'enquiries.delete'}

    def get(self, request, id):
        # Opening an enquiry changes nothing; progress is recorded only by an explicit action.
        return send(enquiry_shape(_load(id, events=True), with_events=True))

    def patch(self, request, id):
        enquiry = _load(id)
        body = validate(EnquiryUpdateBody, request.data)
        if 'adminNotes' in body:
            enquiry.admin_notes = body['adminNotes']
        if 'followUpAt' in body:
            enquiry.follow_up_at = body['followUpAt']
        enquiry.save()
        return send(enquiry_shape(enquiry))

    def delete(self, request, id):
        _load(id).delete()
        return send({'id': str(id)})


class StatusChangeBody(serializers.Serializer):
    status = serializers.ChoiceField(choices=EnquiryStatus.values)
    note = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class EnquiryStatusView(AdminView):
    required_permissions = 'enquiries.edit'

    def patch(self, request, id):
        body = validate(StatusChangeBody, request.data)
        status = body['status']
        actor = actor_of(request)
        with transaction.atomic():
            enquiry = Enquiry.objects.select_for_update().get(pk=_load(id).pk)
            if enquiry.status == status:
                raise ApiError.bad_request(f'That enquiry is already {STATUS_LABELS[status]}.')
            previous = enquiry.status
            for key, value in status_side_effects(status).items():
                setattr(enquiry, key, value)
            # Moving unowned work forward makes the mover its owner.
            auto_assigned = False
            if enquiry.assignee_id is None and not is_closed(status) and status != EnquiryStatus.NEW:
                enquiry.assignee, enquiry.assigned_at, auto_assigned = request.user, timezone.now(), True
            enquiry.save()

            log_event(enquiry, 'status_change', describe_status_change(previous, status), actor=actor,
                      note=body.get('note') or None, meta={'from': previous, 'to': status})
            if auto_assigned:
                log_event(enquiry, 'assigned', f"Assigned to {actor['actor_name']} on taking the enquiry forward",
                          actor=actor, meta={'assigneeId': str(request.user.id), 'automatic': True})
        return send(enquiry_shape(_load(id)))


class AssignBody(serializers.Serializer):
    # Omitted means "assign to me"; null unassigns.
    assigneeId = serializers.UUIDField(required=False, allow_null=True)


class EnquiryAssignView(AdminView):
    """
    Claim, assign, reassign or unassign. Claiming unowned work needs only
    enquiries.edit; moving work to or from someone else needs enquiries.assign.
    """

    required_permissions = 'enquiries.edit'

    def patch(self, request, id):
        body = validate(AssignBody, request.data)
        actor = actor_of(request)
        me = request.user
        claiming = 'assigneeId' not in body
        target_id = me.id if claiming else body['assigneeId']

        with transaction.atomic():
            # Lock only the enquiry row: PostgreSQL refuses FOR UPDATE on the nullable
            # side of the outer join that select_related('assignee') adds.
            enquiry = Enquiry.objects.select_for_update(of=('self',)).select_related('assignee').get(pk=_load(id).pk)
            current_id = enquiry.assignee_id

            if claiming and current_id and current_id != me.id:
                name = enquiry.assignee.name if enquiry.assignee else 'Someone else'
                raise ApiError.conflict(f'{name} is already handling that enquiry.')

            giving_to_other = target_id is not None and target_id != me.id
            taking_from_other = current_id is not None and current_id != me.id
            if (giving_to_other or taking_from_other) and not me.has_dashboard_permission('enquiries.assign'):
                raise ApiError.forbidden('Your role does not include reassigning other people’s enquiries.')
            if current_id == target_id:
                raise ApiError.bad_request('That enquiry is already assigned to them.')

            target = AdminUser.objects.filter(pk=target_id).first() if target_id else None
            if target_id and target is None:
                raise ApiError.bad_request('That account no longer exists.')

            previous_status = enquiry.status
            enquiry.assignee = target
            enquiry.assigned_at = timezone.now() if target else None
            if target and enquiry.status == EnquiryStatus.NEW:
                enquiry.status = EnquiryStatus.ASSIGNED
            if not target and enquiry.status == EnquiryStatus.ASSIGNED:
                enquiry.status = EnquiryStatus.NEW
            enquiry.save()

            if target:
                summary = f"{actor['actor_name']} claimed this enquiry" if claiming else f'Assigned to {target.name}'
            else:
                summary = f"Returned to the unassigned queue by {actor['actor_name']}"
            log_event(enquiry, 'assigned' if target else 'unassigned', summary, actor=actor,
                      meta={'from': str(current_id) if current_id else None, 'to': str(target_id) if target_id else None,
                            'claimed': claiming})
            if enquiry.status != previous_status:
                log_event(enquiry, 'status_change', describe_status_change(previous_status, enquiry.status), actor=actor,
                          meta={'from': previous_status, 'to': enquiry.status, 'automatic': True})
        return send(enquiry_shape(_load(id)))


class NoteBody(serializers.Serializer):
    note = serializers.CharField(min_length=1, max_length=4000, error_messages={'blank': 'A note cannot be empty.'})


class EnquiryNoteView(AdminView):
    required_permissions = 'enquiries.edit'

    def post(self, request, id):
        enquiry = _load(id)
        body = validate(NoteBody, request.data)
        actor = actor_of(request)
        log_event(enquiry, 'note', f"Note added by {actor['actor_name']}", actor=actor, note=body['note'])
        return send(enquiry_shape(_load(id, events=True), with_events=True), status=201)


class ContactedBody(serializers.Serializer):
    note = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    followUpAt = serializers.DateTimeField(required=False, allow_null=True)


class EnquiryContactedView(AdminView):
    """Records that someone actually reached the customer, and optionally when to chase again."""

    required_permissions = 'enquiries.edit'

    def post(self, request, id):
        body = validate(ContactedBody, request.data)
        actor = actor_of(request)
        with transaction.atomic():
            enquiry = Enquiry.objects.select_for_update().get(pk=_load(id).pk)
            now = timezone.now()
            previous_status = enquiry.status
            enquiry.last_contacted_at = now
            if 'followUpAt' in body:
                enquiry.follow_up_at = body['followUpAt']
            # Reaching out is work in progress by definition.
            if enquiry.status in (EnquiryStatus.NEW, EnquiryStatus.ASSIGNED):
                enquiry.status = EnquiryStatus.IN_PROGRESS
            if enquiry.assignee_id is None:
                enquiry.assignee, enquiry.assigned_at = request.user, now
            enquiry.save()

            follow = body.get('followUpAt')
            summary = f"{actor['actor_name']} contacted the customer"
            if follow:
                summary += f', following up {follow.date().isoformat()}'
            log_event(enquiry, 'contacted', summary, actor=actor, note=body.get('note') or None,
                      meta={'followUpAt': follow.isoformat() if follow else None})
            if enquiry.status != previous_status:
                log_event(enquiry, 'status_change', describe_status_change(previous_status, enquiry.status),
                          actor=actor, meta={'from': previous_status, 'to': enquiry.status, 'automatic': True})
        return send(enquiry_shape(_load(id)))


class BulkEnquiryStatusBody(BulkIds):
    status = serializers.ChoiceField(choices=EnquiryStatus.values)


class BulkEnquiryStatusView(AdminView):
    required_permissions = 'enquiries.edit'

    def patch(self, request):
        body = validate(BulkEnquiryStatusBody, request.data)
        actor = actor_of(request)
        with transaction.atomic():
            targets = list(Enquiry.objects.select_for_update().filter(pk__in=body['ids']).exclude(status=body['status']))
            if not targets:
                raise ApiError.not_found('None of those enquiries still exist, or none needed changing.')
            patch = status_side_effects(body['status'])
            Enquiry.objects.filter(pk__in=[t.pk for t in targets]).update(**patch, updated_at=timezone.now())
            EnquiryEvent.objects.bulk_create(
                EnquiryEvent(enquiry=t, type='status_change', summary=describe_status_change(t.status, body['status']),
                             meta={'from': t.status, 'to': body['status'], 'bulk': True}, **actor)
                for t in targets
            )
        return send({'ids': [str(t.pk) for t in targets], 'status': body['status'], 'count': len(targets)})


class BulkAssignBody(BulkIds):
    assigneeId = serializers.UUIDField(allow_null=True)


class BulkEnquiryAssignView(AdminView):
    required_permissions = ('enquiries.edit', 'enquiries.assign')

    def patch(self, request):
        body = validate(BulkAssignBody, request.data)
        actor = actor_of(request)
        target_id = body['assigneeId']
        target = AdminUser.objects.filter(pk=target_id).first() if target_id else None
        if target_id and target is None:
            raise ApiError.bad_request('That account no longer exists.')

        with transaction.atomic():
            qs = Enquiry.objects.select_for_update().filter(pk__in=body['ids'])
            # Explicit: "not assigned to this person" must include unassigned rows.
            qs = qs.filter(assignee__isnull=False) if target is None else qs.filter(Q(assignee__isnull=True) | ~Q(assignee=target))
            targets = list(qs)
            if not targets:
                raise ApiError.not_found('None of those enquiries still exist, or none needed changing.')
            ids = [t.pk for t in targets]
            now = timezone.now()
            Enquiry.objects.filter(pk__in=ids).update(assignee=target, assigned_at=now if target else None, updated_at=now)
            if target:
                Enquiry.objects.filter(pk__in=ids, status=EnquiryStatus.NEW).update(status=EnquiryStatus.ASSIGNED)
            EnquiryEvent.objects.bulk_create(
                EnquiryEvent(
                    enquiry=t,
                    type='assigned' if target else 'unassigned',
                    summary=f'Assigned to {target.name}' if target else 'Returned to the unassigned queue',
                    meta={'from': str(t.assignee_id) if t.assignee_id else None,
                          'to': str(target_id) if target_id else None, 'bulk': True},
                    **actor,
                )
                for t in targets
            )
        return send({'ids': [str(i) for i in ids], 'assigneeId': str(target_id) if target_id else None, 'count': len(ids)})


class BulkEnquiryDeleteView(AdminView):
    required_permissions = 'enquiries.delete'

    def delete(self, request):
        body = validate(BulkIds, request.data)
        # delete() counts cascaded timeline rows too, so count the enquiries first.
        ids = [str(i) for i in Enquiry.objects.filter(pk__in=body['ids']).values_list('pk', flat=True)]
        if not ids:
            raise ApiError.not_found('None of those enquiries still exist.')
        Enquiry.objects.filter(pk__in=ids).delete()
        return send({'ids': ids, 'count': len(ids)})


class EnquiryOptionsView(PublicView):
    """The contact form's interest list, so the form and the validator never disagree."""

    def get(self, request):
        return send({'interests': INTERESTS, 'currencies': ['KES', 'USD']})
