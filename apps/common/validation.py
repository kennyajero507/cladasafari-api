"""
Input validation building blocks.

Request bodies and query strings are validated with DRF serializers used purely
as schemas: `validate(Schema, data)` returns the cleaned dict or raises a
ValidationError that the exception handler flattens into `error.details`.

Field names are camelCase because they are the wire names the web app sends.
Conversion to model attributes happens in each app's write functions, not by
DRF's `source=` machinery, which keeps partial updates explicit.
"""
from rest_framework import serializers

STATUS_CHOICES = ('draft', 'published')


def validate(schema_cls, data, *, partial: bool = False) -> dict:
    schema = schema_cls(data=data, partial=partial)
    schema.is_valid(raise_exception=True)
    return dict(schema.validated_data)


def query_dict(request) -> dict:
    """QueryDict -> plain dict of first values (lists are never used in queries here)."""
    return {key: request.query_params.get(key) for key in request.query_params}


class BlankToNoneCharField(serializers.CharField):
    """Trims, and turns an empty string into None so blank form fields do not overwrite data."""

    def __init__(self, **kwargs):
        kwargs.setdefault('required', False)
        kwargs.setdefault('allow_blank', True)
        kwargs.setdefault('allow_null', True)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        return value or None


class SearchField(BlankToNoneCharField):
    def __init__(self, **kwargs):
        kwargs.setdefault('max_length', 120)
        super().__init__(**kwargs)


class BooleanString(serializers.ChoiceField):
    """`?featured=true` style flags: accepts the strings 'true'/'false' only."""

    def __init__(self, **kwargs):
        kwargs.setdefault('required', False)
        super().__init__(choices=('true', 'false'), **kwargs)

    def to_internal_value(self, data):
        return super().to_internal_value(data) == 'true'


class PaginationQuery(serializers.Serializer):
    page = serializers.IntegerField(min_value=1, default=1)
    limit = serializers.IntegerField(min_value=1, max_value=100, default=12)


class ImageSchema(serializers.Serializer):
    url = serializers.CharField(max_length=500, error_messages={'blank': 'An image URL is required.'})
    alt = serializers.CharField(max_length=300, error_messages={'blank': 'Alt text is required for accessibility.'})
    caption = serializers.CharField(max_length=300, required=False, allow_blank=True)


class OptionalImageSchema(serializers.Serializer):
    url = serializers.CharField(max_length=500, required=False, allow_blank=True)
    alt = serializers.CharField(max_length=300, required=False, allow_blank=True)


class SeoSchema(serializers.Serializer):
    metaTitle = serializers.CharField(max_length=70, required=False, allow_blank=True)
    metaDescription = serializers.CharField(max_length=180, required=False, allow_blank=True)
    ogImage = serializers.CharField(max_length=500, required=False, allow_blank=True)


class StatusBody(serializers.Serializer):
    status = serializers.ChoiceField(choices=STATUS_CHOICES)


class BulkIds(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.UUIDField(error_messages={'invalid': 'That is not a valid id.'}),
        min_length=1,
        max_length=100,
        error_messages={'min_length': 'Select at least one item.'},
    )


class BulkStatus(BulkIds):
    status = serializers.ChoiceField(choices=STATUS_CHOICES)


class StringList(serializers.ListField):
    def __init__(self, max_items: int = 100, item_max: int = 300, **kwargs):
        kwargs.setdefault('required', False)
        super().__init__(child=serializers.CharField(max_length=item_max, allow_blank=False), max_length=max_items, **kwargs)
