from django.db import models

from apps.common.models import BaseModel, PublishableModel
from apps.media.models import ImageAsset


class Tag(models.Model):
    name = models.CharField(max_length=40, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class BlogPost(PublishableModel):
    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=160, unique=True)
    excerpt = models.CharField(max_length=300)
    # A small Markdown subset: ## headings, **bold**, *italic*, "- " bullets.
    content = models.TextField()
    cover_image = models.ForeignKey(ImageAsset, on_delete=models.PROTECT, related_name='+')
    author_name = models.CharField(max_length=120, default='Clada Safari Bliss')
    author_avatar = models.CharField(max_length=500, blank=True, default='')
    tags = models.ManyToManyField(Tag, blank=True, related_name='posts')
    reading_minutes = models.PositiveIntegerField(default=4)
    published_at = models.DateTimeField(db_index=True)
    featured = models.BooleanField(default=False)
    seo = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-published_at']

    def __str__(self):
        return self.title


class Testimonial(PublishableModel):
    author_name = models.CharField(max_length=120)
    author_location = models.CharField(max_length=120, blank=True, default='')
    avatar = models.JSONField(null=True, blank=True)
    quote = models.CharField(max_length=600)
    rating = models.PositiveSmallIntegerField(default=5)
    tour = models.ForeignKey('catalog.Tour', null=True, blank=True, on_delete=models.SET_NULL, related_name='testimonials')
    tour_name = models.CharField(max_length=140, blank=True, default='')
    travelled_on = models.DateField(null=True, blank=True)
    featured = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-featured', 'order', '-created_at']

    def __str__(self):
        return f'{self.author_name}: {self.quote[:40]}'


class FaqGroup(models.TextChoices):
    GENERAL = 'general', 'General'
    BOOKING = 'booking', 'Booking'
    TRAVEL = 'travel', 'Travel'
    PAYMENT = 'payment', 'Payment'


class Faq(PublishableModel):
    question = models.CharField(max_length=240, unique=True)
    answer = models.TextField()
    group = models.CharField(max_length=10, choices=FaqGroup.choices, default=FaqGroup.GENERAL)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['group', 'order']
        verbose_name = 'FAQ'

    def __str__(self):
        return self.question


class Service(PublishableModel):
    """Something the company does for clients, shown on /services."""

    title = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120, unique=True)
    summary = models.CharField(max_length=300)
    body = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=40, blank=True, default='compass')
    image = models.ForeignKey(ImageAsset, null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    highlights = models.JSONField(default=list, blank=True)
    cta_label = models.CharField(max_length=60, blank=True, default='')
    cta_href = models.CharField(max_length=200, blank=True, default='')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'title']

    def __str__(self):
        return self.title


class PageTemplate(models.TextChoices):
    """How the web app lays a page out. Content is the same shape for all three."""

    STANDARD = 'standard', 'Standard'
    LEGAL = 'legal', 'Legal / policy'
    CONTACT = 'contact', 'Contact'


class Page(PublishableModel):
    """
    An editable static page: About Us, Contact, Privacy Policy, Terms, FAQs...

    Served at /<slug> on the site. `body` is the same small Markdown subset as
    blog posts (## headings, **bold**, *italic*, "- " bullets, [links](/path)),
    rendered without raw HTML so pasted markup can never run script.
    `sections` holds typed blocks laid out after the body (see
    resources.SECTION_SCHEMAS). `contact` is used by the contact template only:
    extra emails, phones and offices; blank parts fall back to Site settings.
    """

    title = models.CharField(max_length=140)
    slug = models.SlugField(max_length=140, unique=True)
    template = models.CharField(max_length=20, choices=PageTemplate.choices, default=PageTemplate.STANDARD)
    eyebrow = models.CharField(max_length=80, blank=True, default='')
    subtitle = models.CharField(max_length=300, blank=True, default='')
    hero_image = models.ForeignKey(ImageAsset, null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    body = models.TextField(blank=True, default='')
    sections = models.JSONField(default=list, blank=True)
    contact = models.JSONField(default=dict, blank=True)
    seo = models.JSONField(null=True, blank=True)
    show_in_footer = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'title']

    def __str__(self):
        return self.title


class SiteSettings(BaseModel):
    """
    Singleton (key='primary') holding site-wide copy and imagery.

    Each section is JSON because it is read and written whole by the settings
    screen and never queried into. Images inside it use the same {url, alt}
    shape as everywhere else and are registered in the media library by the
    seed, so their credits are still recorded.
    """

    key = models.CharField(max_length=20, unique=True, default='primary')
    hero = models.JSONField(default=dict)
    hero_slides = models.JSONField(default=list)
    values = models.JSONField(default=list)
    contact = models.JSONField(default=dict)
    socials = models.JSONField(default=dict)
    newsletter = models.JSONField(default=dict)
    footer_blurb = models.TextField(blank=True, default='')
    video = models.JSONField(default=dict)
    seo = models.JSONField(default=dict)
    promo = models.JSONField(default=dict)
    about = models.JSONField(default=dict)
    home = models.JSONField(default=dict)
    pages = models.JSONField(default=dict)
    notice = models.JSONField(default=dict)
    brand = models.JSONField(default=dict)
    # The public site menu, as arranged in the dashboard. Empty means the menu
    # is built automatically from the category tree.
    navigation = models.JSONField(default=list)
    # The floating WhatsApp chat: on/off, an optional number of its own, the
    # greeting and the quick-reply chips.
    whatsapp_widget = models.JSONField(default=dict)

    class Meta:
        verbose_name = 'site settings'
        verbose_name_plural = 'site settings'

    # Wire name -> model attribute.
    SECTIONS = {
        'hero': 'hero',
        'heroSlides': 'hero_slides',
        'values': 'values',
        'contact': 'contact',
        'socials': 'socials',
        'newsletter': 'newsletter',
        'footerBlurb': 'footer_blurb',
        'video': 'video',
        'seo': 'seo',
        'promo': 'promo',
        'about': 'about',
        'home': 'home',
        'pages': 'pages',
        'notice': 'notice',
        'brand': 'brand',
        'navigation': 'navigation',
        'whatsappWidget': 'whatsapp_widget',
    }

    def as_dict(self) -> dict:
        return {wire: getattr(self, attr) for wire, attr in self.SECTIONS.items()}

    def __str__(self):
        return 'Site settings'
