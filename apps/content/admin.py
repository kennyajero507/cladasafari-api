from django.contrib import admin

from .models import BlogPost, Faq, Page, Service, SiteSettings, Tag, Testimonial


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'published_at', 'featured', 'is_sample')
    list_filter = ('status', 'featured', 'is_sample', 'tags')
    search_fields = ('title', 'excerpt')
    filter_horizontal = ('tags',)


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('author_name', 'rating', 'tour_name', 'status', 'is_sample')
    list_filter = ('status', 'is_sample', 'rating')


@admin.register(Faq)
class FaqAdmin(admin.ModelAdmin):
    list_display = ('question', 'group', 'order', 'status', 'is_sample')
    list_filter = ('group', 'status')


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'status', 'is_sample')


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    """The dashboard's Pages screen is the main editor; this is the superuser fallback."""

    list_display = ('title', 'slug', 'template', 'status', 'show_in_footer', 'order', 'updated_at')
    list_filter = ('template', 'status', 'show_in_footer', 'is_sample')
    list_editable = ('order',)
    search_fields = ('title', 'subtitle', 'body')
    prepopulated_fields = {'slug': ('title',)}
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'template', 'status', 'show_in_footer', 'order')}),
        ('Banner', {'fields': ('eyebrow', 'subtitle', 'hero_image')}),
        ('Content', {'fields': ('body', 'sections'), 'description': 'Body uses the blog Markdown subset. Sections are typed JSON blocks; prefer the dashboard editor.'}),
        ('Contact template', {'fields': ('contact',), 'classes': ('collapse',)}),
        ('SEO and provenance', {'fields': ('seo', 'is_sample', 'source_note'), 'classes': ('collapse',)}),
    )


admin.site.register(Tag)
admin.site.register(SiteSettings)
