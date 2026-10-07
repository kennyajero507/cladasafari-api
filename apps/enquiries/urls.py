from django.urls import path

from . import views

urlpatterns = [
    path('enquiries', views.SubmitEnquiryView.as_view()),
    path('enquiries/options', views.EnquiryOptionsView.as_view()),
    path('admin/enquiries', views.EnquiryListView.as_view()),
    path('admin/enquiries/assignable', views.AssignableStaffView.as_view()),
    path('admin/enquiries/bulk/status', views.BulkEnquiryStatusView.as_view()),
    path('admin/enquiries/bulk/assign', views.BulkEnquiryAssignView.as_view()),
    path('admin/enquiries/bulk', views.BulkEnquiryDeleteView.as_view()),
    path('admin/enquiries/<uuid:id>', views.EnquiryDetailView.as_view()),
    path('admin/enquiries/<uuid:id>/status', views.EnquiryStatusView.as_view()),
    path('admin/enquiries/<uuid:id>/assignee', views.EnquiryAssignView.as_view()),
    path('admin/enquiries/<uuid:id>/notes', views.EnquiryNoteView.as_view()),
    path('admin/enquiries/<uuid:id>/contacted', views.EnquiryContactedView.as_view()),
]
