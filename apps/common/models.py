import uuid

from django.db import models


class Status(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    PUBLISHED = 'published', 'Published'


class BaseModel(models.Model):
    """UUID primary key plus timestamps; every API resource derives from this."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class PublishableModel(BaseModel):
    """
    Draft/published content that may be seed or demo material.

    `is_sample` marks records generated to populate the site (demo tours,
    placeholder testimonials, example blog posts) as opposed to information
    taken from the business's own website. It is shown in the dashboard and,
    for testimonials, on the public site, so demo content is never mistaken
    for the real thing.
    """

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True)
    is_sample = models.BooleanField(
        default=False,
        help_text='Generated demo content, not information supplied by the business.',
    )
    # Where the record's content came from, e.g. which fields are from the
    # original website and which were drafted and still need confirming.
    source_note = models.CharField(max_length=300, blank=True, default='')

    class Meta:
        abstract = True
