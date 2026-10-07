import re
import unicodedata


def slugify(value: str) -> str:
    """
    URL-safe slug. Strips diacritics ("Zürich" -> "zurich") and drops
    apostrophes rather than hyphenating them ("Kenya's" -> "kenyas").
    """
    text = unicodedata.normalize('NFKD', str(value))
    text = ''.join(ch for ch in text if not unicodedata.combining(ch)).lower().strip()
    text = re.sub(r"['’]", '', text)
    text = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    return text[:96]


def unique_slug(model, source: str, exclude_id=None, field: str = 'slug') -> str:
    """
    First free slug for `model`, appending -2, -3, ... as needed.

    Check-then-write, so two concurrent creates can still collide; the column's
    UNIQUE constraint turns the loser into a 409 rather than a duplicate row.
    """
    base = slugify(source) or 'item'
    candidate, suffix = base, 1
    while True:
        qs = model.objects.filter(**{field: candidate})
        if exclude_id is not None:
            qs = qs.exclude(pk=exclude_id)
        if not qs.exists():
            return candidate
        suffix += 1
        candidate = f'{base}-{suffix}'
