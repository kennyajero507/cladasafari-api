from django.contrib import admin

from .models import ImageAsset


@admin.register(ImageAsset)
class ImageAssetAdmin(admin.ModelAdmin):
    list_display = ('title', 'url', 'source', 'photographer', 'width', 'height')
    list_filter = ('source',)
    search_fields = ('title', 'url', 'alt', 'photographer')
