import json
import secrets
from pathlib import Path

from django.conf import settings
from django.db.models import ProtectedError, Q
from PIL import Image, UnidentifiedImageError
from rest_framework import serializers

from apps.accounts.auth import AdminView, PublicView
from apps.common.exceptions import ApiError
from apps.common.responses import page_meta, paginate, send
from apps.common.slugs import slugify
from apps.common.validation import PaginationQuery, SearchField, query_dict, validate

from .models import ImageAsset
from .services import asset_shape

# Pillow format -> (extension, MIME type). The file's own bytes decide, not the
# Content-Type the browser claimed.
ALLOWED_FORMATS = {
    'JPEG': ('.jpg', 'image/jpeg'),
    'PNG': ('.png', 'image/png'),
    'WEBP': ('.webp', 'image/webp'),
    'AVIF': ('.avif', 'image/avif'),
}


def _in_settings(url: str) -> bool:
    from apps.content.models import SiteSettings

    row = SiteSettings.objects.filter(key='primary').first()
    return bool(row) and url in json.dumps(row.as_dict())


class UploadView(AdminView):
    required_permissions = 'media.upload'

    def post(self, request):
        upload = request.FILES.get('file')
        if upload is None:
            raise ApiError.bad_request('No image was received.')
        if upload.size > settings.UPLOAD_MAX_BYTES:
            raise ApiError.bad_request('That image is larger than the 6MB limit.')

        try:
            with Image.open(upload) as probe:
                fmt = probe.format
                width, height = probe.size
                probe.verify()
        except (UnidentifiedImageError, OSError, SyntaxError):
            raise ApiError.bad_request('Only JPEG, PNG, WebP or AVIF images are accepted.')
        if fmt not in ALLOWED_FORMATS:
            raise ApiError.bad_request('Only JPEG, PNG, WebP or AVIF images are accepted.')

        ext, mimetype = ALLOWED_FORMATS[fmt]
        stem = slugify(Path(upload.name).stem)[:40] or 'image'
        # Random suffix: same-named uploads never overwrite one another.
        filename = f'{stem}-{secrets.token_hex(6)}{ext}'

        upload.seek(0)
        settings.MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
        with open(settings.MEDIA_ROOT / filename, 'wb') as out:
            for chunk in upload.chunks():
                out.write(chunk)

        # The URL is stored on content and rendered by the public site, so it
        # must be this API's public origin, never localhost in production.
        url = f'{settings.PUBLIC_API_URL}{settings.MEDIA_URL}{filename}'
        asset = ImageAsset.objects.create(
            url=url,
            alt=stem.replace('-', ' ').capitalize(),
            title=stem.replace('-', ' '),
            source=ImageAsset.Source.UPLOAD,
            license='Supplied by Clada Safari Bliss',
            width=width,
            height=height,
            size_bytes=upload.size,
            file=filename,
        )
        return send(
            {'id': str(asset.id), 'url': url, 'filename': filename, 'size': upload.size, 'mimetype': mimetype},
            status=201,
        )


class UploadDeleteView(AdminView):
    """
    The dashboard calls this when it drops an upload it has just made (the
    editor replaced or cleared the image before saving). Files still referenced
    by content are left alone rather than breaking a published page.
    """

    required_permissions = 'media.upload'

    def delete(self, request, filename):
        if filename != Path(filename).name or filename.startswith('.'):
            raise ApiError.bad_request('That is not a valid filename.')
        target = (settings.MEDIA_ROOT / filename).resolve()
        if target.parent != settings.MEDIA_ROOT.resolve():
            raise ApiError.bad_request('That is not a valid filename.')

        asset = ImageAsset.objects.filter(file=filename).first()
        if asset is not None:
            if _in_settings(asset.url):
                return send({'filename': filename, 'deleted': False, 'inUse': True})
            try:
                asset.delete()
            except ProtectedError:
                return send({'filename': filename, 'deleted': False, 'inUse': True})

        target.unlink(missing_ok=True)
        return send({'filename': filename, 'deleted': True})


MEDIA_SORTS = {'newest': ['-created_at'], 'oldest': ['created_at'], 'title-asc': ['title', 'url']}


class MediaQuery(PaginationQuery):
    q = SearchField()
    source = serializers.ChoiceField(choices=ImageAsset.Source.values, required=False)
    sort = serializers.ChoiceField(choices=list(MEDIA_SORTS), required=False)


def _media_list(request):
    q = validate(MediaQuery, query_dict(request))
    qs = ImageAsset.objects.all()
    if q.get('source'):
        qs = qs.filter(source=q['source'])
    if q.get('q'):
        term = q['q']
        qs = qs.filter(Q(alt__icontains=term) | Q(title__icontains=term) | Q(photographer__icontains=term) | Q(url__icontains=term))
    qs = qs.order_by(*MEDIA_SORTS.get(q.get('sort'), ['title', 'url']))
    rows, total = paginate(qs, q['page'], q['limit'])
    return send([asset_shape(a) for a in rows], meta=page_meta(q['page'], q['limit'], total))


class PublicMediaView(PublicView):
    """Image credits, for the public photo-credits page."""

    def get(self, request):
        return _media_list(request)


class AdminMediaListView(AdminView):
    required_permissions = 'media.view'

    def get(self, request):
        return _media_list(request)


class MediaUpdateBody(serializers.Serializer):
    alt = serializers.CharField(max_length=300, required=False)
    caption = serializers.CharField(max_length=300, required=False, allow_blank=True)
    title = serializers.CharField(max_length=160, required=False, allow_blank=True)
    photographer = serializers.CharField(max_length=120, required=False, allow_blank=True)
    sourceUrl = serializers.URLField(max_length=500, required=False, allow_blank=True)
    license = serializers.CharField(max_length=120, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    tags = serializers.ListField(child=serializers.CharField(max_length=40), required=False, max_length=30)


class AdminMediaDetailView(AdminView):
    required_permissions = {'GET': 'media.view', 'PATCH': 'media.upload', 'DELETE': 'media.delete'}

    def _get(self, id) -> ImageAsset:
        asset = ImageAsset.objects.filter(pk=id).first()
        if asset is None:
            raise ApiError.not_found('We could not find that image.')
        return asset

    def get(self, request, id):
        return send(asset_shape(self._get(id)))

    def patch(self, request, id):
        asset = self._get(id)
        body = validate(MediaUpdateBody, request.data, partial=True)
        mapping = {'sourceUrl': 'source_url'}
        for key, value in body.items():
            setattr(asset, mapping.get(key, key), value)
        asset.save()
        return send(asset_shape(asset))

    def delete(self, request, id):
        asset = self._get(id)
        if _in_settings(asset.url):
            raise ApiError.conflict('That image is used in the site settings. Replace it there first.')
        try:
            asset.delete()
        except ProtectedError:
            raise ApiError.conflict('That image is still used by published content. Replace it there first.')
        if asset.file:
            (settings.MEDIA_ROOT / asset.file.name).unlink(missing_ok=True)
        return send({'id': str(id), 'deleted': True})
