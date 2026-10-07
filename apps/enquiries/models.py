from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class EnquiryType(models.TextChoices):
    CONTACT = 'contact', 'Contact form'
    BOOKING = 'booking', 'Booking request'


class EnquiryStatus(models.TextChoices):
    """
    The pipeline, in order. `new` means nobody owns it yet; from `assigned`
    on it has an owner. `won` and `lost` are both terminal and kept distinct
    so the two outcomes can be counted.
    """

    NEW = 'new', 'New'
    ASSIGNED = 'assigned', 'Assigned'
    IN_PROGRESS = 'in_progress', 'In progress'
    QUOTED = 'quoted', 'Quoted'
    WON = 'won', 'Booked'
    LOST = 'lost', 'Closed'


OPEN_STATUSES = [EnquiryStatus.NEW, EnquiryStatus.ASSIGNED, EnquiryStatus.IN_PROGRESS, EnquiryStatus.QUOTED]
CLOSED_STATUSES = {EnquiryStatus.WON, EnquiryStatus.LOST}


class Enquiry(BaseModel):
    type = models.CharField(max_length=10, choices=EnquiryType.choices)
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True, default='')

    # Contact form
    interest = models.CharField(max_length=60, blank=True, default='')
    budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    budget_currency = models.CharField(max_length=3, blank=True, default='')
    message = models.TextField(blank=True, default='')

    # Booking form
    tour = models.ForeignKey('catalog.Tour', null=True, blank=True, on_delete=models.SET_NULL, related_name='enquiries')
    tour_title = models.CharField(max_length=140, blank=True, default='')
    travel_date = models.DateField(null=True, blank=True)
    guests = models.JSONField(null=True, blank=True)  # {adults, children, infants}

    # "ENQ-2609-0042": quoted on the phone and in email subjects.
    reference = models.CharField(max_length=20, unique=True, null=True, blank=True)

    status = models.CharField(max_length=12, choices=EnquiryStatus.choices, default=EnquiryStatus.NEW, db_index=True)
    admin_notes = models.TextField(blank=True, default='')
    source = models.CharField(max_length=40, default='website')
    is_sample = models.BooleanField(default=False, help_text='Demo enquiry created by the seed.')

    # SET_NULL: removing a staff account returns their work to the pool.
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_enquiries'
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    last_contacted_at = models.DateTimeField(null=True, blank=True)
    follow_up_at = models.DateTimeField(null=True, blank=True, db_index=True)
    # Stamped once on reaching a terminal state, so time-to-close is cheap to measure.
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'enquiries'
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['assignee', 'status']),
        ]

    def __str__(self):
        return f'{self.reference or self.pk} {self.name}'


class EnquiryReferenceCounter(models.Model):
    """
    One row per month holding the last sequence number issued, so references
    are allocated under a row lock instead of read-then-guess (which hands
    concurrent submissions the same number).
    """

    period = models.CharField(max_length=4, primary_key=True)  # 'YYMM'
    last_seq = models.PositiveIntegerField(default=0)


class EnquiryEventType(models.TextChoices):
    CREATED = 'created', 'Created'
    STATUS_CHANGE = 'status_change', 'Status change'
    ASSIGNED = 'assigned', 'Assigned'
    UNASSIGNED = 'unassigned', 'Unassigned'
    NOTE = 'note', 'Note'
    CONTACTED = 'contacted', 'Contacted'


class EnquiryEvent(BaseModel):
    """Append-only activity timeline for one enquiry. Corrections are new entries."""

    enquiry = models.ForeignKey(Enquiry, on_delete=models.CASCADE, related_name='events')
    type = models.CharField(max_length=16, choices=EnquiryEventType.choices)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    # Kept beside the FK so a deleted account still reads as a name.
    actor_name = models.CharField(max_length=120, blank=True, null=True)
    summary = models.CharField(max_length=300)
    note = models.TextField(blank=True, null=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['enquiry', 'created_at'])]
