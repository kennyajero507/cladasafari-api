from django.db import models

from apps.common.models import BaseModel


class ImageAsset(BaseModel):
    """
    One image the site can show, with the metadata that belongs to the image
    rather than to wherever it happens to be used: alt text, credit and origin.

    Tours, destinations, places, posts and services point at these rows rather
    than embedding URL strings, so a credit or alt-text correction is made once
    and a photograph's provenance can always be traced.
    """

    class Source(models.TextChoices):
        ORIGINAL = 'original', 'Original Clada Safari Bliss website'
        PEXELS = 'pexels', 'Pexels'
        UPLOAD = 'upload', 'Uploaded in the dashboard'
        OTHER = 'other', 'Other'

    # Either a site-relative path served by the web app (/images/...) or an
    # absolute URL (uploads served by this API).
    url = models.CharField(max_length=500, unique=True)
    alt = models.CharField(max_length=300)
    caption = models.CharField(max_length=300, blank=True, default='')
    title = models.CharField(max_length=160, blank=True, default='', help_text='Short internal name.')

    source = models.CharField(max_length=12, choices=Source.choices, default=Source.OTHER, db_index=True)
    photographer = models.CharField(max_length=120, blank=True, default='')
    source_url = models.URLField(max_length=500, blank=True, default='')
    pexels_id = models.PositiveBigIntegerField(null=True, blank=True)
    license = models.CharField(max_length=120, blank=True, default='')
    notes = models.TextField(blank=True, default='')

    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    tags = models.JSONField(default=list, blank=True)

    # Set only for files uploaded through the dashboard.
    file = models.ImageField(upload_to='', null=True, blank=True)
    size_bytes = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title or self.url

    @property
    def credit_line(self) -> str:
        if self.source == self.Source.PEXELS:
            return f'Photo by {self.photographer} on Pexels' if self.photographer else 'Photo from Pexels'
        # Photos from the original site carry no credit line: who took them, and
        # under what licence, has not been confirmed (see `notes`).
        if self.source == self.Source.ORIGINAL:
            return ''
        return self.photographer
