from django.urls import path

from . import views

urlpatterns = [
    path('media', views.PublicMediaView.as_view()),
    path('admin/media', views.AdminMediaListView.as_view()),
    path('admin/media/<uuid:id>', views.AdminMediaDetailView.as_view()),
    path('admin/uploads', views.UploadView.as_view()),
    path('admin/uploads/<str:filename>', views.UploadDeleteView.as_view()),
]
