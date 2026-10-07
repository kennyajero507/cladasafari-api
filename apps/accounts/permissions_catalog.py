"""
The permission vocabulary.

Every admin endpoint is gated by one of these strings. They are grouped by
resource because the dashboard's role editor renders a section per group and a
checkbox per permission: adding one here makes it appear there with no further
work.

`publish` is separate from `edit` on purpose: the common request is a writer
who may draft and revise but not put anything in front of the public.
"""

CONTENT_RESOURCES = [
    ('tours', 'Tours & packages'),
    ('destinations', 'Destinations'),
    ('categories', 'Categories'),
    ('blog', 'Blog posts'),
    ('testimonials', 'Testimonials'),
    ('faqs', 'FAQs'),
    ('services', 'Services'),
    ('pages', 'Pages'),
]

CONTENT_VERBS = [
    ('view', 'View', 'See the list and open records, including drafts.'),
    ('create', 'Create', 'Add new records.'),
    ('edit', 'Edit', 'Change existing records.'),
    ('publish', 'Publish', 'Move between draft and published.'),
    ('delete', 'Delete', 'Permanently remove records.'),
]

_content_groups = [
    {
        'key': key,
        'label': label,
        'permissions': [{'key': f'{key}.{verb}', 'label': verb_label, 'hint': hint} for verb, verb_label, hint in CONTENT_VERBS],
    }
    for key, label in CONTENT_RESOURCES
]

PERMISSION_GROUPS = [
    *_content_groups,
    {
        'key': 'enquiries',
        'label': 'Enquiries',
        'permissions': [
            {'key': 'enquiries.view', 'label': 'View', 'hint': 'Read enquiries and customer contact details.'},
            {
                'key': 'enquiries.edit',
                'label': 'Triage',
                'hint': 'Move an enquiry through the pipeline, claim unassigned ones, and add notes.',
            },
            {
                'key': 'enquiries.assign',
                'label': 'Assign to others',
                'hint': 'Hand an enquiry to another member of staff. Claiming unassigned work needs only Triage.',
            },
            {'key': 'enquiries.delete', 'label': 'Delete', 'hint': 'Permanently remove enquiries.'},
        ],
    },
    {
        'key': 'media',
        'label': 'Media library',
        'permissions': [
            {'key': 'media.view', 'label': 'View', 'hint': 'Browse the image library and its credits.'},
            {'key': 'media.upload', 'label': 'Upload', 'hint': 'Add images and edit their alt text and credits.'},
            {'key': 'media.delete', 'label': 'Delete', 'hint': 'Remove images that nothing uses any more.'},
        ],
    },
    {
        'key': 'settings',
        'label': 'Site settings',
        'permissions': [
            {
                'key': 'settings.edit',
                'label': 'Edit settings',
                'hint': 'Contact details, hero, values and SEO. Affects every public page.',
            },
        ],
    },
    {
        'key': 'users',
        'label': 'Users and roles',
        'permissions': [
            {'key': 'users.view', 'label': 'View users', 'hint': 'See the list of dashboard accounts.'},
            {'key': 'users.manage', 'label': 'Manage users', 'hint': 'Invite, edit and remove accounts.'},
            {
                'key': 'roles.manage',
                'label': 'Manage roles',
                'hint': 'Create roles and change what they may do. Effectively grants everything.',
            },
            {'key': 'audit.view', 'label': 'View audit log', 'hint': 'See who changed access and when.'},
        ],
    },
]

ALL_PERMISSIONS = [p['key'] for group in PERMISSION_GROUPS for p in group['permissions']]
_PERMISSION_SET = set(ALL_PERMISSIONS)


def is_permission(value: str) -> bool:
    return value in _PERMISSION_SET


_content_permissions = [p['key'] for g in _content_groups for p in g['permissions']]

SYSTEM_ROLES = [
    {
        'name': 'Administrator',
        'description': 'Full access to everything, including users, roles and site settings.',
        'locked': True,
        'permissions': ALL_PERMISSIONS,
    },
    {
        'name': 'Editor',
        'description': 'Creates, edits, publishes and deletes all content. No access to users or settings.',
        'locked': False,
        'permissions': [
            *_content_permissions,
            'enquiries.view',
            'enquiries.edit',
            'media.view',
            'media.upload',
            'media.delete',
        ],
    },
    {
        'name': 'Author',
        'description': 'Writes and edits content but cannot publish or delete it.',
        'locked': False,
        'permissions': [
            *[p for p in _content_permissions if not p.endswith(('.publish', '.delete'))],
            'media.view',
            'media.upload',
        ],
    },
    {
        'name': 'Travel Consultant',
        'description': 'Handles incoming enquiries and bookings. Can read, but not change, published content.',
        'locked': False,
        'permissions': [
            'enquiries.view',
            'enquiries.edit',
            'enquiries.assign',
            'tours.view',
            'destinations.view',
        ],
    },
]
