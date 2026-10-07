"""
Countries, categories and tours.

WHAT COMES FROM WHERE
---------------------
Everything here is taken from the live Clada Safari Bliss website
(cladasafaribliss.com):

- CATEGORIES is its main menu, in its order and with its labels: Local,
  Getaways, International and Safari Packages, each with the places beneath it.
  Category slugs are the live site's own (/ba_locations/<slug>/), so the web
  app can redirect the old addresses.
- TOURS (tours.py) is its 49 package pages: title, overview, "from" price,
  duration and gallery, and the "Things To Do" list as highlights.

What the live site does not have is left empty rather than written for it:
there are no day-by-day itineraries, inclusion or exclusion lists, group sizes
or reviews there. Add them in the dashboard as the business supplies them.

Ten packages show "$0.00" on the live site. They are seeded with a price of 0,
which the web app prints as "Price on request". Seven have no stated length
and are seeded with 0 days, which hides the duration.

Four rows are seeded as drafts (see `note` on each in tours.py): three have no
description or price on the live site, and one is a leftover duplicate.
"""
from .tours import TOURS  # noqa: F401  (re-exported for the seed command)

ORIGINAL_NOTE = (
    'Title, overview, price, duration and photographs from cladasafaribliss.com. '
    'Itinerary, inclusions and exclusions are not on that site and are still to be added.'
)
SAMPLE_NOTE = 'Demo package created for this build; not on the original website.'
DESTINATION_NOTE = 'Destination copy written for this build.'

# Countries are the filterable tags on a package; none has a destination page yet.
COUNTRIES = [
    {'name': 'Kenya', 'slug': 'kenya', 'iso_code': 'KE', 'region': 'east-africa', 'order': 1},
    {'name': 'Tanzania', 'slug': 'tanzania', 'iso_code': 'TZ', 'region': 'east-africa', 'order': 2},
    {'name': 'United Arab Emirates', 'slug': 'united-arab-emirates', 'iso_code': 'AE', 'region': 'middle-east', 'order': 10},
    {'name': 'Mauritius', 'slug': 'mauritius', 'iso_code': 'MU', 'region': 'africa', 'order': 11},
    {'name': 'South Africa', 'slug': 'south-africa', 'iso_code': 'ZA', 'region': 'africa', 'order': 12},
]


def _group(slug, name, kind, order, description, children):
    """One menu group and the places beneath it, as flat category rows."""
    rows = [{
        'slug': slug, 'name': name, 'kind': kind, 'order': order, 'eyebrow': '', 'nav_label': name,
        'description': description, 'image': None,
    }]
    for index, (child_slug, child_name) in enumerate(children, start=1):
        rows.append({
            'slug': child_slug, 'parent': slug, 'name': child_name, 'kind': kind, 'order': index,
            'eyebrow': name, 'nav_label': child_name, 'description': '', 'image': None,
        })
    return rows


# The live menu, exactly: four groups and their places. Samburu and East Africa
# Safaris are in the menu but have no published package yet, as on the live site.
# Group descriptions are short introductions written for this build. No category
# has a picture: the live site's photographs are 400px wide, too small for a
# listing banner, so listings use the banner image from Site settings instead.
CATEGORIES = [
    *_group(
        'local', 'Local', 'local', 1,
        'Beach breaks on the Kenyan coast and short safaris in the parks, priced in Kenya shillings.',
        [
            ('mombasa', 'Mombasa'),
            ('diani', 'Diani'),
            ('malindi-watamu', 'Malindi/Watamu'),
            ('amboseli', 'Amboseli'),
            ('tsavo', 'Tsavo'),
            ('samburu', 'Samburu'),
            ('maasai-mara', 'Maasai Mara'),
        ],
    ),
    *_group(
        'getaways', 'Getaways', 'local', 2,
        'Short escapes from Nairobi to the Rift Valley lakes and Mount Kenya.',
        [
            ('nakuru', 'Nakuru'),
            ('naivasha', 'Naivasha'),
            ('elementaita', 'Elementaita'),
            ('mt-kenya', 'Mt Kenya'),
        ],
    ),
    *_group(
        'international', 'International', 'international', 3,
        'Holiday packages to Dubai, Mauritius and Cape Town.',
        [
            ('dubai', 'Dubai'),
            ('mauritius', 'Mauritius'),
            ('capetown', 'Capetown'),
        ],
    ),
    *_group(
        'safari-packages', 'Safari Packages', 'safari', 4,
        'Budget, midrange and luxury safaris across Kenya and Tanzania.',
        [
            ('kenyanon-residents', 'Kenya(Non-residents)'),
            ('tanzania', 'Tanzania'),
            ('east-africa-safaris', 'East Africa Safaris'),
        ],
    ),
]

# Country pages and regional areas: none on the live site, so none are seeded.
# Both can be added later (destinations in the dashboard, areas in Django admin).
DESTINATIONS = []
AREAS = []
AREA_DETAILS = {}
AREA_TOURS = {}
