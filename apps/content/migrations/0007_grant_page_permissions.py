"""
Existing roles get `pages.*` wherever they already hold the same `services.*`
verb, so Editors can manage pages and Authors can draft them straight after
upgrading. The locked Administrator role holds everything already.
"""
from django.db import migrations

VERBS = ('view', 'create', 'edit', 'publish', 'delete')


def grant(apps, schema_editor):
    Role = apps.get_model('accounts', 'Role')
    for role in Role.objects.filter(locked=False):
        held = list(role.permissions or [])
        added = [f'pages.{v}' for v in VERBS if f'services.{v}' in held and f'pages.{v}' not in held]
        if added:
            role.permissions = held + added
            role.save(update_fields=['permissions'])


def revoke(apps, schema_editor):
    Role = apps.get_model('accounts', 'Role')
    for role in Role.objects.filter(locked=False):
        kept = [p for p in role.permissions or [] if not p.startswith('pages.')]
        if kept != role.permissions:
            role.permissions = kept
            role.save(update_fields=['permissions'])


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
        ('content', '0006_pages'),
    ]

    operations = [migrations.RunPython(grant, revoke)]
