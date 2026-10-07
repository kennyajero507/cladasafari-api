"""
Services and the editable pages.

Services restate what the live Clada Safari Bliss website says the company
does (its menu, its About Us page and its Air Ticketing page), so they are not
flagged as samples.

The live site has no FAQs, customer reviews or blog of its own, so none are
seeded: FAQS, TESTIMONIALS and BLOG_POSTS are empty and their sections stay off
the public site until real ones are added in the dashboard. Invented reviews
or policies would be a false claim. There are no demo staff or enquiries
either, so the dashboard starts clean.
"""

SERVICES = [
    {
        'title': 'Safari Packages', 'icon': 'compass', 'image': 'clada-2025-03-3.jpg', 'order': 1,
        'summary': 'Budget, midrange and luxury safaris across Kenya and Tanzania.',
        'body': 'Safaris in the Maasai Mara, Amboseli, Tsavo and Samburu, and across the border in Tanzania, '
                'with tailor made itineraries aligned with your budget.',
        'highlights': ['Kenya and Tanzania', 'Budget, midrange and luxury options', 'Tailor made itineraries'],
        'cta': ('See safari packages', '/tours?category=safari-packages'),
    },
    {
        'title': 'Local Holidays and Getaways', 'icon': 'leaf', 'image': 'clada-2025-05-4-1.jpg', 'order': 2,
        'summary': 'Holidays on the Kenyan coast, short safaris in the parks and getaways to the Rift Valley lakes.',
        'body': 'Mombasa, Diani and Malindi/Watamu on the coast; Amboseli, Tsavo and the Maasai Mara; and '
                'getaways to Nakuru, Naivasha, Elementaita and Mt Kenya.',
        'highlights': ['Mombasa, Diani and Malindi/Watamu', 'Amboseli, Tsavo and Maasai Mara', 'Nakuru, Naivasha, Elementaita and Mt Kenya'],
        'cta': ('See local packages', '/tours?category=local'),
    },
    {
        'title': 'International Packages', 'icon': 'globe', 'image': 'clada-2025-02-1-5.jpg', 'order': 3,
        'summary': 'Holiday packages to Dubai, Mauritius and Cape Town.',
        'body': 'City, beach and island holidays beyond East Africa, planned with the same personal touch.',
        'highlights': ['Dubai', 'Mauritius', 'Cape Town'],
        'cta': ('See international packages', '/tours?category=international'),
    },
    {
        'title': 'Air Ticketing', 'icon': 'receipt', 'image': 'clada-2025-05-1-8.jpg', 'order': 4,
        'summary': 'We help you find, book and manage flights.',
        'body': 'Flight search and recommendations, booking assistance, ticket issuance, payment processing, '
                'changes and cancellations, special requests and support throughout your journey.',
        'highlights': ['Flight search and recommendations', 'Group and multi-destination bookings', 'Changes and cancellations handled'],
        'cta': ('About air ticketing', '/air-ticketing'),
    },
]

FAQS = []
TESTIMONIALS = []
BLOG_POSTS = []
STAFF = []
ENQUIRIES = []

# The live Air Ticketing page, verbatim, as the blog Markdown subset.
AIR_TICKETING = (
    'Air ticketing, as a service offered by us, involves assisting customers in finding, booking, and managing '
    'flights. We provide a personalized experience by offering expert advice, guidance, and access to a wide '
    'range of airlines and flight options. Here’s what our air ticketing service typically includes:\n\n'
    '- **Flight Search and Recommendations:** We help you find the best flights based on your preferences, such '
    'as travel dates, destinations, budget, and class of service. We can also recommend the most suitable '
    'airlines, routes, and layovers based on your needs.\n'
    '- **Booking Assistance:** Once you’ve selected your flight, we handle the entire booking process, ensuring '
    'that all details are correct and that the best prices are secured. We also assist with group bookings, '
    'complex itineraries, or multi-destination trips.\n'
    '- **Ticket Issuance:** After booking, we issue your flight ticket, typically in electronic form (e-ticket), '
    'and provide you with all necessary flight details, including booking reference numbers, seat assignments, '
    'and travel guidelines.\n'
    '- **Payment Processing:** We process payment for tickets, offering multiple payment options. We also handle '
    'any payment-related issues, such as billing discrepancies or installment plans.\n'
    '- **Changes and Cancellations:** If there are any changes to your travel plans, such as flight date changes '
    'or cancellations, we assist in rebooking or refunding tickets, handle airline policies, and ensure minimal '
    'hassle for you.\n'
    '- **Special Requests:** We can also assist with special services, such as booking additional baggage, '
    'arranging meal preferences, and requesting assistance for passengers with reduced mobility.\n'
    '- **Customer Support:** Throughout your journey, we offer ongoing support, including helping with issues at '
    'the airport, assisting with missed connections, or rebooking if there are delays or cancellations.'
)


def pages(defaults: dict) -> list[dict]:
    """
    The editable static pages. About, Contact and Air Ticketing carry the live
    website's own copy. The policy pages are drafts with an outline only: the
    live Terms & Conditions page is an unedited placeholder, and legal text has
    to come from the business, so they stay hidden until someone writes them.
    """
    about, banners, contact = defaults['about'], defaults['pages'], defaults['contact']
    policy_note = 'Outline only. Replace with the business\'s own policy, reviewed by a lawyer, before publishing.'
    return [
        {
            'slug': 'about', 'title': banners['about']['title'], 'template': 'standard', 'order': 0,
            'subtitle': banners['about']['subtitle'], 'hero_image': banners['about']['image'],
            'status': 'published', 'show_in_footer': False,
            'seo': {'metaTitle': 'About Us', 'metaDescription': defaults['seo']['defaultDescription'][:180]},
            'source_note': 'Company Profile, Mission, Vision and Values from the About Us page of cladasafaribliss.com.',
            'sections': [
                {'id': 'story', 'type': 'imageText', 'eyebrow': about['intro'], 'heading': about['heading'],
                 'body': '\n\n'.join(about['paragraphs']), 'images': about['images'][:2], 'imageSide': 'right'},
                {'id': 'pillars', 'type': 'cards', 'tone': 'dark', 'eyebrow': defaults['brand']['tagline'],
                 'heading': 'Mission, vision and values',
                 'items': [{'eyebrow': '', 'title': p['title'], 'body': p['body'], 'href': '', 'linkLabel': ''}
                           for p in about['pillars']]},
                {'id': 'values', 'type': 'cards', 'tone': 'light', 'eyebrow': 'How we work',
                 'heading': 'What you can expect',
                 'items': [{'eyebrow': '', 'title': v['title'], 'body': v['description'], 'href': '', 'linkLabel': ''}
                           for v in defaults['values']]},
                {'id': 'cta', 'type': 'cta', 'tone': 'dark', 'eyebrow': '', 'heading': f'Find us at {contact["addressLine"]}',
                 'body': f'{contact["supportHours"]}.', 'ctaLabel': 'Contact us', 'ctaHref': '/contact'},
            ],
        },
        {
            'slug': 'contact', 'title': banners['contact']['title'], 'template': 'contact', 'order': 1,
            'subtitle': banners['contact']['subtitle'], 'hero_image': banners['contact']['image'],
            'status': 'published', 'show_in_footer': False,
            'seo': {'metaTitle': 'Contact Us',
                    'metaDescription': 'Reach out to Clada Safari Bliss to begin planning your trip: questions, bookings and travel arrangements.'},
            # Empty lists: details come from Site settings › Contact until set here.
            'contact': {'emails': [], 'phones': [], 'offices': [], 'hours': '', 'socials': {}, 'showForm': True,
                        'formHeading': 'Get In Touch'},
            'source_note': 'Details follow Site settings › Contact.',
        },
        {
            'slug': 'air-ticketing', 'title': 'Air Ticketing', 'template': 'standard', 'order': 2,
            'subtitle': 'Finding, booking and managing your flights.', 'hero_image': banners['services']['image'],
            'status': 'published', 'show_in_footer': False,
            'seo': {'metaTitle': 'Air Ticketing',
                    'metaDescription': 'Flight search, booking, ticket issuance, changes and support from Clada Safari Bliss.'},
            'source_note': 'Copy from the Air Ticketing page of cladasafaribliss.com.',
            'sections': [
                {'id': 'service', 'type': 'text', 'eyebrow': 'Our services', 'heading': 'Air Ticketing', 'body': AIR_TICKETING},
                {'id': 'ask', 'type': 'cta', 'tone': 'dark', 'eyebrow': '', 'heading': 'Inquire about an air ticket',
                 'body': 'Tell us your route and dates and we will come back with flight options.',
                 'ctaLabel': 'Inquire About Air Ticket', 'ctaHref': '/contact?interest=Air%20Ticketing'},
            ],
        },
        {
            'slug': 'privacy-policy', 'title': 'Privacy Policy', 'template': 'legal', 'order': 10,
            'subtitle': '', 'hero_image': None, 'status': 'draft', 'show_in_footer': True, 'is_sample': True,
            'source_note': policy_note,
            'body': (
                '## Who we are\n\nReplace with the business\'s legal name and contact details.\n\n'
                '## What we collect\n\nReplace with what the enquiry and booking forms collect, and why.\n\n'
                '## How we use it\n\nReplace with how enquiries are handled and who sees them.\n\n'
                '## How long we keep it\n\nReplace with the retention period.\n\n'
                '## Your rights\n\nReplace with how people can see, correct or delete their data, '
                'in line with the Kenya Data Protection Act, 2019.'
            ),
        },
        {
            'slug': 'terms-and-conditions', 'title': 'Terms & Conditions', 'template': 'legal', 'order': 11,
            'subtitle': '', 'hero_image': None, 'status': 'draft', 'show_in_footer': True, 'is_sample': True,
            'source_note': policy_note,
            'body': (
                '## Bookings\n\nReplace with how a booking is confirmed.\n\n'
                '## Payments\n\nReplace with deposit and balance terms.\n\n'
                '## Cancellations and changes\n\nReplace with the cancellation and amendment policy.\n\n'
                '## Travel documents\n\nReplace with who is responsible for passports, visas and insurance.'
            ),
        },
    ]
