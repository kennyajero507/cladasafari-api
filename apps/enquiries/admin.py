from django.contrib import admin

from .models import Enquiry, EnquiryEvent


class EventInline(admin.TabularInline):
    model = EnquiryEvent
    extra = 0
    readonly_fields = ('created_at', 'type', 'actor_name', 'summary', 'note')
    fields = readonly_fields


@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ('reference', 'name', 'type', 'status', 'assignee', 'created_at', 'is_sample')
    list_filter = ('status', 'type', 'is_sample')
    search_fields = ('reference', 'name', 'email')
    inlines = [EventInline]
