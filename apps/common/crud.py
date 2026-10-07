"""
Draft/published collections that share one shape: listed with filters,
fetched by slug in public and by id in the dashboard, and edited through the
same verbs (create, update, publish, delete, bulk publish, bulk delete).

Rather than near-identical view sets per model, each resource is described by
a `Resource` and its views are generated from it. Tours use it too, with a
richer `apply()`; only the enquiry pipeline and accounts are hand-written.

Permissions follow the catalogue in accounts/permissions_catalog.py:
    <perm>.view / .create / .edit / .publish / .delete
Changing `status` is publishing, so an edit that also flips status needs both.
"""
from dataclasses import dataclass, field
from typing import Any, Callable

from django.db import models, transaction
from django.db.models import Q
from django.urls import path

from apps.accounts.auth import AdminView, PublicView, require

from .exceptions import ApiError
from .responses import page_meta, paginate, send
from .revalidate import revalidate
from .slugs import unique_slug
from .validation import BulkIds, BulkStatus, StatusBody, query_dict, validate


@dataclass
class Resource:
    model: type[models.Model]
    label: str  # "tour", used in messages
    perm: str  # permission prefix, e.g. "tours"
    path: str  # URL segment, e.g. "tours"
    shape: Callable[[Any], dict]
    create_schema: type
    update_schema: type
    list_query: type
    apply: Callable[[Any, dict, bool], None]
    title_field: str | None = 'title'
    slug_field: str | None = 'slug'
    search_fields: list[str] = field(default_factory=list)
    sorts: dict[str, list[str]] = field(default_factory=dict)
    default_sort: list[str] = field(default_factory=lambda: ['order', '-created_at'])
    filter: Callable[[Any, dict], Any] = lambda qs, q: qs
    queryset: Callable[[], Any] | None = None
    tags: Callable[[Any], list[str]] = lambda obj: []
    # Public detail lookup; None disables the public detail route.
    public_detail: bool = True
    public_list: bool = True

    def base_qs(self):
        return self.queryset() if self.queryset else self.model.objects.all()

    def not_found(self):
        return ApiError.not_found(f'We could not find that {self.label}.')


def _list(resource: Resource, request, *, published_only: bool):
    q = validate(resource.list_query, query_dict(request))
    qs = resource.base_qs()
    if published_only:
        qs = qs.filter(status='published')
    elif q.get('status'):
        qs = qs.filter(status=q['status'])
    qs = resource.filter(qs, q)

    term = q.get('q')
    if term and resource.search_fields:
        cond = Q()
        for name in resource.search_fields:
            cond |= Q(**{f'{name}__icontains': term})
        qs = qs.filter(cond)

    qs = qs.order_by(*resource.sorts.get(q.get('sort'), resource.default_sort))
    rows, total = paginate(qs, q['page'], q['limit'])
    return send([resource.shape(r) for r in rows], meta=page_meta(q['page'], q['limit'], total))


def _load(resource: Resource, id):
    obj = resource.base_qs().filter(pk=id).first()
    if obj is None:
        raise resource.not_found()
    return obj


def _save(resource: Resource, obj, data: dict, creating: bool):
    """Slug handling shared by create and update, then the resource's own apply()."""
    if resource.slug_field:
        requested = data.pop('slug', None)
        current = getattr(obj, resource.slug_field, None)
        if creating:
            source = requested or data.get(resource.title_field) or resource.label
            setattr(obj, resource.slug_field, unique_slug(resource.model, source))
        elif requested and requested != current:
            setattr(obj, resource.slug_field, unique_slug(resource.model, requested, exclude_id=obj.pk))
        # Otherwise the slug is kept: renaming must not break a published URL.
    with transaction.atomic():
        resource.apply(obj, data, creating)
    revalidate(resource.tags(obj))


def build_views(resource: Resource):
    r = resource

    class PublicList(PublicView):
        def get(self, request):
            return _list(r, request, published_only=True)

    class PublicDetail(PublicView):
        def get(self, request, slug):
            obj = r.base_qs().filter(**{r.slug_field: slug, 'status': 'published'}).first()
            if obj is None:
                raise r.not_found()
            return send(r.shape(obj))

    class AdminList(AdminView):
        required_permissions = {'GET': f'{r.perm}.view', 'POST': f'{r.perm}.create'}

        def get(self, request):
            return _list(r, request, published_only=False)

        def post(self, request):
            data = validate(r.create_schema, request.data)
            if data.get('status') == 'published':
                require(request, f'{r.perm}.publish')
            obj = r.model()
            _save(r, obj, data, creating=True)
            return send(r.shape(_load(r, obj.pk)), status=201)

    class AdminDetail(AdminView):
        required_permissions = {'GET': f'{r.perm}.view', 'PATCH': f'{r.perm}.edit', 'DELETE': f'{r.perm}.delete'}

        def get(self, request, id):
            return send(r.shape(_load(r, id)))

        def patch(self, request, id):
            obj = _load(r, id)
            data = validate(r.update_schema, request.data, partial=True)
            if 'status' in data and data['status'] != getattr(obj, 'status', None):
                require(request, f'{r.perm}.publish')
            _save(r, obj, data, creating=False)
            return send(r.shape(_load(r, obj.pk)))

        def delete(self, request, id):
            obj = _load(r, id)
            tags = r.tags(obj)
            try:
                obj.delete()
            except models.ProtectedError:
                raise ApiError.conflict(f'That {r.label} is still in use elsewhere and cannot be deleted.')
            revalidate(tags)
            return send({'id': str(id)})

    class AdminStatus(AdminView):
        required_permissions = f'{r.perm}.publish'

        def patch(self, request, id):
            obj = _load(r, id)
            obj.status = validate(StatusBody, request.data)['status']
            obj.save(update_fields=['status', 'updated_at'])
            revalidate(r.tags(obj))
            return send(r.shape(obj))

    class BulkStatusView(AdminView):
        required_permissions = f'{r.perm}.publish'

        def patch(self, request):
            data = validate(BulkStatus, request.data)
            rows = list(r.model.objects.filter(pk__in=data['ids']))
            if not rows:
                raise ApiError.not_found(f'None of those {r.label}s still exist.')
            r.model.objects.filter(pk__in=[o.pk for o in rows]).update(status=data['status'])
            revalidate([t for o in rows for t in r.tags(o)])
            return send({'ids': [str(o.pk) for o in rows], 'status': data['status'], 'count': len(rows)})

    class BulkDeleteView(AdminView):
        required_permissions = f'{r.perm}.delete'

        def delete(self, request):
            data = validate(BulkIds, request.data)
            rows = list(r.model.objects.filter(pk__in=data['ids']))
            if not rows:
                raise ApiError.not_found(f'None of those {r.label}s still exist.')
            tags = [t for o in rows for t in r.tags(o)]
            try:
                with transaction.atomic():
                    r.model.objects.filter(pk__in=[o.pk for o in rows]).delete()
            except models.ProtectedError:
                raise ApiError.conflict(f'At least one of those {r.label}s is still in use and cannot be deleted.')
            revalidate(tags)
            return send({'ids': [str(o.pk) for o in rows], 'count': len(rows)})

    urls = []
    if r.public_list:
        urls.append(path(r.path, PublicList.as_view()))
    if r.public_detail and r.slug_field:
        urls.append(path(f'{r.path}/<str:slug>', PublicDetail.as_view()))
    urls += [
        path(f'admin/{r.path}', AdminList.as_view()),
        # Bulk routes before <uuid:id>; the converter already keeps them apart,
        # but the order documents intent.
        path(f'admin/{r.path}/bulk/status', BulkStatusView.as_view()),
        path(f'admin/{r.path}/bulk', BulkDeleteView.as_view()),
        path(f'admin/{r.path}/<uuid:id>', AdminDetail.as_view()),
        path(f'admin/{r.path}/<uuid:id>/status', AdminStatus.as_view()),
    ]
    return urls


def assign(obj, data: dict, mapping: dict[str, str]) -> None:
    """Copy wire keys present in `data` onto model attributes named in `mapping`."""
    for wire, attr in mapping.items():
        if wire in data:
            setattr(obj, attr, data[wire])
