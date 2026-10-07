from django.db import migrations

OLD = 'Prototype — content and prices are placeholders.'
NEW = 'Prices are per person and subject to availability at the time of booking.'


def swap(apps, old, new):
    SiteSettings = apps.get_model('content', 'SiteSettings')
    for row in SiteSettings.objects.all():
        # Only touch the untouched default; an admin's own wording is kept.
        if (row.notice or {}).get('text') == old:
            row.notice = {**row.notice, 'text': new}
            row.save(update_fields=['notice'])


def forwards(apps, schema_editor):
    swap(apps, OLD, NEW)


def backwards(apps, schema_editor):
    swap(apps, NEW, OLD)


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0002_blogpost_source_note_faq_source_note_and_more'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
