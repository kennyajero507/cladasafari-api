"""
Default site-settings content.

Copy marked [source] is taken verbatim, or near-verbatim, from the live Clada
Safari Bliss website (cladasafaribliss.com): its homepage slider, About Us and
Contact Us pages. Everything else is supporting copy written for this build and
can be edited in the dashboard.

The live site shows social icons but links none of them, so `socials` is empty.
"""

IMG = '/images'

ZEBRA = {'url': f'{IMG}/clada-2026-09-pexels-redrum-visuals-5819228-scaled.jpg', 'alt': 'A herd of zebra grazing on open plains'}
CHEETAHS = {'url': f'{IMG}/clada-2026-10-pexels-magda-ehlers-pexels-39257491.jpg', 'alt': 'Two cheetahs at a kill on dry grassland'}
STAGS = {'url': f'{IMG}/clada-2026-09-pexels-stephen-leonardi-587681991-28614276-scaled.jpg', 'alt': 'Two stags locking antlers in dry grass'}

ABOUT_PARAGRAPHS = [  # [source] About Us > Company Profile
    'Clada Safari Bliss Limited was established to offer elegant boutique travel experiences. Our founder '
    'and CEO, Beatrice Macharia, had a vision to provide personalized itineraries after travelling to various '
    'parts of the world and being excited to see how different people experience the same locations differently.',
    'The desire in her to provide customized tour services, tailor made to exceed the customers’ expectations '
    'while working with local service providers to create beautiful memories, birthed this tour company: Clada '
    'Safari Bliss Limited, a private travel and tours company registered in Kenya, Africa. With a vibrant team '
    'which has a wide range of travel experiences in different capacities, we present diverse offerings to '
    'serve our clients in exceptional ways.',
]

SITE_SETTINGS_DEFAULTS = {
    'brand': {
        'name': 'Clada Safari Bliss',  # [source]
        'tagline': 'Beyond Magical',  # [source] About Us
        'logo': {'url': '/brand/logo.png', 'alt': 'Clada Safari Bliss'},
        'logoCompact': {'url': '/brand/logo.png', 'alt': 'Clada Safari Bliss'},
        'logoOnLight': {'url': '/brand/logo.png', 'alt': 'Clada Safari Bliss'},
        'mark': {'url': '/brand/logo-mark.png', 'alt': 'Clada Safari Bliss'},
    },
    'hero': {
        'eyebrow': 'Top African Safaris',  # [source] slider
        'title': 'Explore Best African Safaris',  # [source] slider
        'subtitle': 'Thrilling experiences for the explorer in you.',  # [source] slider
        'backgroundImage': ZEBRA,
        'primaryCta': {'label': 'Safari Packages', 'href': '/tours?category=safari-packages'},
        'secondaryCta': {'label': 'Local Packages', 'href': '/tours?category=local'},
    },
    # The three photographs in the live homepage slider.
    'heroSlides': [ZEBRA, CHEETAHS, STAGS],
    # Each value restates something the live About Us page says about the company.
    'values': [
        {
            'title': 'Tailor-made itineraries',
            'description': 'Safari itineraries with a personal touch, aligned with your budget.',
            'icon': 'compass',
            'image': {'url': f'{IMG}/clada-2025-03-1.jpg', 'alt': 'A safari vehicle watching an elephant beside a dirt track'},
        },
        {
            'title': 'Logistics handled',
            'description': 'Air ticketing, train ticketing and transfers, so you can focus on the trip.',
            'icon': 'receipt',
            'image': {'url': f'{IMG}/clada-2025-02-1-5.jpg', 'alt': 'The Burj Khalifa above Dubai at dusk'},
        },
        {
            'title': 'Advisors on call',
            'description': 'A dedicated team of travel advisors, available to answer your concerns any day.',
            'icon': 'clock',
            'image': {'url': f'{IMG}/clada-2025-05-2-8.jpg', 'alt': 'A zebra with an oxpecker on its neck'},
        },
        {
            'title': 'Trusted local providers',
            'description': 'We work with reliable local service providers to create beautiful memories.',
            'icon': 'leaf',
            'image': {'url': f'{IMG}/clada-2025-05-4-1.jpg', 'alt': 'Palms above a white-sand beach on the Kenyan coast'},
        },
    ],
    'contact': {
        'phone': '+254 727 999 944',  # [source]
        'whatsapp': '+254 727 999 944',  # [source] the live site's WhatsApp button
        'email': 'info@cladasafaribliss.com',  # [source]
        'addressLine': 'Marist Lane, Karen',  # [source]
        'poBox': '',
        'city': 'Nairobi, Kenya',
        'supportHours': 'Mon to Sat 7.00 am – 8.00 pm, Sunday 8.00 am – 6.00 pm',  # [source]
    },
    'socials': {},
    'newsletter': {
        'heading': 'Our Newsletter',  # [source] footer
        'blurb': 'Occasional updates on new packages and safari seasons.',
    },
    'footerBlurb': (
        'Clada Safari Bliss Limited is a private travel and tours company registered in Kenya, offering '
        'elegant boutique travel experiences.'
    ),
    # Empty until an administrator adds the company's own film.
    'video': {},
    'seo': {
        'defaultTitle': 'Clada Safari Bliss',
        'defaultDescription': (
            'Tailor-made safaris in Kenya and Tanzania, Kenyan coast holidays, weekend getaways and '
            'international packages from Clada Safari Bliss, Nairobi.'
        ),
        'ogImage': ZEBRA['url'],
    },
    'promo': {
        'eyebrow': 'Air Ticketing',
        'title': 'Flights found, booked and managed for you.',
        'body': (  # [source] Air Ticketing page, shortened
            'We help you find the best flights for your dates, destination, budget and class of service, '
            'then handle the booking, the ticket and any changes.'
        ),
        'cta': {'label': 'About air ticketing', 'href': '/air-ticketing'},
        'image': CHEETAHS,
    },
    'about': {
        'title': 'About Us',  # [source]
        'intro': 'Your loyal travel companion',  # [source]
        'heading': 'Company Profile',  # [source]
        'paragraphs': ABOUT_PARAGRAPHS,
        'images': [ZEBRA, {'url': f'{IMG}/clada-2025-05-4-1.jpg', 'alt': 'Palms above a white-sand beach on the Kenyan coast'}],
        'pillars': [
            {'title': 'Our Mission', 'eyebrow': '', 'href': '',  # [source]
             'body': 'Our mission is to curate unforgettable and exceptional boutique travel experiences for our '
                     'clients in the most elegant way possible. From safaris in the adventurous Kenya’s terrains, '
                     'to holidays in pristine turquoise waters along the Kenyan South Coast and beyond, we offer '
                     'tailor made safari itineraries with a personal touch aligned with client’s budget.'},
            {'title': 'Our Vision', 'eyebrow': '', 'href': '',  # [source]
             'body': 'We provide travel logistics such as air ticketing, train ticketing and transfers to '
                     'facilitate seamless movement across different locations for our guests. We take the lead in '
                     'ensuring you focus on your travel as we manage your logistics for a flawless boutique travel '
                     'experience.'},
            {'title': 'Our Values', 'eyebrow': '', 'href': '',  # [source]
             'body': 'Our team is defined by PRACITE. We passionately listen to deliver your travel requirements '
                     'in a reliable, accountable and creative way, leaving a favorable impact on all those we come '
                     'across. You can trust us to deliver with excellence.'},
        ],
    },
    'home': {
        'packagesEyebrow': 'Hand-picked',
        'packagesTitle': 'Popular packages',
        'destinationsEyebrow': 'Where we go',
        'destinationsTitle': 'Top destinations',
        'testimonialsImage': ZEBRA,
        'ctaTitle': 'Have a question? Contact us!',  # [source] Contact Us
        'ctaBody': (  # [source] Contact Us
            'Reach out to Clada Safari Bliss today to begin planning your unforgettable adventure. Our friendly '
            'team is ready to assist you with any questions, bookings or travel arrangements.'
        ),
        'ctaImage': CHEETAHS,
    },
    # Banner copy and imagery for each top-level page.
    'pages': {
        'tours': {
            'title': 'Packages & Safaris',
            'subtitle': 'Local holidays, getaways, international packages and safaris.',
            'image': ZEBRA,
        },
        'destinations': {'title': 'Destinations', 'subtitle': '', 'image': ZEBRA},
        'services': {
            'title': 'What we do',
            'subtitle': 'Safaris, holidays and the travel logistics around them.',
            'image': CHEETAHS,
        },
        'about': {'title': 'About Us', 'subtitle': 'Your loyal travel companion', 'image': ZEBRA},
        'contact': {
            'title': 'Contact Us',
            'subtitle': 'Our friendly team is ready to assist you with any questions, bookings or travel arrangements.',
            'image': CHEETAHS,
        },
        'blog': {'title': 'Travel Journal', 'subtitle': '', 'image': ZEBRA},
        'credits': {'title': 'Photo credits', 'subtitle': 'Where the photographs on this site come from.', 'image': ZEBRA},
    },
    # Footer notice on how prices are quoted. The live site gives "from" prices
    # without saying what they are per, so this does not either.
    'notice': {'enabled': True, 'text': 'Prices are a guide and subject to availability at the time of booking.'},
    # Empty: the web app builds the menu from the category tree (the live site's
    # own menu) until an admin arranges one under Navigation menu.
    'navigation': [],
    # A blank number uses contact.whatsapp, then contact.phone.
    'whatsappWidget': {
        'enabled': True,
        'number': '',
        'greeting': 'Hi there 👋 Tell us where you would like to go and we will reply on WhatsApp.',
        'quickReplies': [
            'Inquire about a safari package',
            'Kenyan coast holiday',
            'International package',
            'Air ticketing',
        ],
    },
}
