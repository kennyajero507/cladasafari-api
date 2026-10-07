"""
Conversion between the wire image shape and ImageAsset rows.

The public API keeps the compact shape the web app renders,

    { url, alt, caption?, credit?, sourceUrl?, width?, height? }

and the admin forms send `{url, alt, caption?}` back. resolve_image() turns
that into an ImageAsset, creating one for a URL the library has not seen
(e.g. an upload) and updating alt text/caption when the editor changed them.
"""
from .models import ImageAsset


def image_shape(asset: ImageAsset | None) -> dict | None:
    if asset is None:
        return None
    shape = {'url': asset.url, 'alt': asset.alt}
    if asset.caption:
        shape['caption'] = asset.caption
    credit = asset.credit_line
    if credit:
        shape['credit'] = credit
    if asset.source_url:
        shape['sourceUrl'] = asset.source_url
    # Known for seeded and uploaded files; lets the web app avoid stretching a
    # small photograph across a full-width banner.
    if asset.width and asset.height:
        shape['width'], shape['height'] = asset.width, asset.height
    return shape


def asset_shape(asset: ImageAsset) -> dict:
    """The full library record, for the dashboard's media screen and /api/media."""
    return {
        'id': str(asset.id),
        '_id': str(asset.id),
        'url': asset.url,
        'alt': asset.alt,
        'caption': asset.caption,
        'title': asset.title,
        'source': asset.source,
        'photographer': asset.photographer,
        'sourceUrl': asset.source_url,
        'pexelsId': asset.pexels_id,
        'license': asset.license,
        'credit': asset.credit_line,
        'width': asset.width,
        'height': asset.height,
        'tags': asset.tags,
        'notes': asset.notes,
        'createdAt': asset.created_at,
        'updatedAt': asset.updated_at,
    }


def resolve_image(data: dict | None) -> ImageAsset | None:
    if not data or not data.get('url'):
        return None
    url = data['url'].strip()
    alt = (data.get('alt') or '').strip()
    caption = (data.get('caption') or '').strip()

    asset = ImageAsset.objects.filter(url=url).first()
    if asset is None:
        return ImageAsset.objects.create(
            url=url,
            alt=alt or 'Image',
            caption=caption,
            source=ImageAsset.Source.UPLOAD if '/uploads/' in url else ImageAsset.Source.OTHER,
        )

    changed = []
    if alt and alt != asset.alt:
        asset.alt = alt
        changed.append('alt')
    if 'caption' in data and caption != asset.caption:
        asset.caption = caption
        changed.append('caption')
    if changed:
        asset.save(update_fields=[*changed, 'updated_at'])
    return asset
