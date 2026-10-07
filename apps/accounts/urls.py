from django.urls import path

from . import views

urlpatterns = [
    path('auth/login', views.LoginView.as_view()),
    path('auth/logout', views.LogoutView.as_view()),
    path('auth/me', views.MeView.as_view()),
    path('admin/users', views.UserListView.as_view()),
    path('admin/users/<uuid:id>', views.UserDetailView.as_view()),
    path('admin/permissions', views.PermissionCatalogueView.as_view()),
    path('admin/roles', views.RoleListView.as_view()),
    path('admin/roles/<uuid:id>', views.RoleDetailView.as_view()),
    path('admin/audit', views.AuditListView.as_view()),
]
