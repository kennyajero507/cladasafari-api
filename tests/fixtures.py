"""
Records the tests need that the seed does not load.

The seed carries only what is on cladasafaribliss.com: no destination pages,
travel areas, blog posts, stock photographs, staff or enquiries. Those
features are still part of the API, so the tests build a small set of each
here, on top of the seeded packages. None of this reaches a real database.
"""
from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import AdminUser, Role
from apps.catalog.models import Country, Destination, Place, Tour, TravelArea
from apps.content.models import BlogPost, Tag
from apps.enquiries.services import create_with_reference, log_event
from apps.media.models import ImageAsset

PHOTO = '/images/clada-2025-05-4-1.jpg'

# area slug -> (name, package slugs). "6-days-amboseli-mara" is in two areas on
# purpose: a group must count it once.
KENYAN_AREAS = {
    'diani': ('Diani', ['3-days-diani', '5-days-diani']),
    'watamu-malindi': ('Watamu/Malindi', []),
    'maasai-mara': ('Maasai Mara', ['3-days-masai-mara', 'maasai-mara-3-days-2-nights-safari',
                                    '6-days-luxury-samburu-mara', '6-days-amboseli-mara']),
    'amboseli': ('Amboseli', ['3-days-amboseli', '6-days-amboseli-mara']),
    'tsavo': ('Tsavo', ['3-days-tsavo']),
}


def _destination(name, iso, region, places=()):
    country, _ = Country.objects.get_or_create(
        iso_code=iso, defaults={'name': name, 'slug': name.lower(), 'region': region})
    image = ImageAsset.objects.get(url=PHOTO)
    dest = Destination.objects.create(
        name=name, slug=name.lower(), country=country, overview=f'{name} for the tests.',
        hero_image=image, card_image=image, featured=True, status='published')
    for index, place in enumerate(places):
        Place.objects.create(destination=dest, name=place, slug=place.lower().replace(' ', '-').replace('/', '-'),
                             kind='Place', image=image, order=index)
    return dest


def load():
    photo = ImageAsset.objects.get(url=PHOTO)

    # A stock photograph with a credit line, for the media and page-credit tests.
    ImageAsset.objects.create(
        url='/images/test-stock.jpg', alt='A stock photograph', source=ImageAsset.Source.PEXELS,
        photographer='Test Photographer', pexels_id=1, source_url='https://www.pexels.com/photo/1/',
        license='Pexels License', width=1920, height=1280)

    # Destination pages: two the packages visit, two they do not.
    _destination('Kenya', 'KE', 'east-africa', [name for name, _ in KENYAN_AREAS.values()])
    _destination('Tanzania', 'TZ', 'east-africa')
    _destination('France', 'FR', 'europe', ['Paris'])
    _destination('Italy', 'IT', 'europe')

    # One package that crosses a border, so it belongs to two destinations.
    Tour.objects.get(slug='5-days-budget-tanzania-safari').countries.add(Country.objects.get(iso_code='KE'))

    # Travel areas: a Kenyan group shaped like the homepage cards, and a second group.
    kenyan = TravelArea.objects.create(name='Kenyan', slug='kenyan', order=1, status='published')
    for index, (slug, (name, tours)) in enumerate(KENYAN_AREAS.items()):
        area = TravelArea.objects.create(
            name=name, slug=slug, parent=kenyan, order=index, status='published',
            tag='Local / Kenya', description=f'{name} in a sentence.', image=photo)
        area.places.set(Place.objects.filter(destination__slug='kenya', name=name))
        for tour in Tour.objects.filter(slug__in=tours):
            tour.areas.add(area)
    abroad = TravelArea.objects.create(name='International', slug='abroad', order=2, status='published')
    dubai = TravelArea.objects.create(name='Dubai', slug='dubai-area', parent=abroad, order=0, status='published')
    for tour in Tour.objects.filter(category__slug='dubai'):
        tour.areas.add(dubai)

    post = BlogPost.objects.create(
        title='When to go on safari', slug='when-to-go-on-safari', excerpt='A test post.', content='## Seasons\n\nText.',
        cover_image=photo, published_at=timezone.now() - timedelta(days=3), status='published', is_sample=True)
    post.tags.set([Tag.objects.get_or_create(name='safari')[0]])

    # Enquiries: one nobody has picked up, and one a consultant owns and is late following up.
    consultant = AdminUser.objects.create_user(
        email='fixture.consultant@example.com', name='Fixture consultant', role=Role.objects.get(name='Travel Consultant'),
        is_sample=True)
    now = timezone.now()
    fresh = create_with_reference(
        type='contact', name='New Enquirer', email='new@example.com', message='Tell me about safaris please.',
        status='new', source='website', is_sample=True)
    log_event(fresh, 'created', 'Contact enquiry received')
    owned = create_with_reference(
        type='contact', name='Waiting Customer', email='waiting@example.com', message='Any news on my quote?',
        status='in_progress', assignee=consultant, assigned_at=now - timedelta(days=4),
        follow_up_at=now - timedelta(days=1), source='website', is_sample=True)
    log_event(owned, 'created', 'Contact enquiry received')
