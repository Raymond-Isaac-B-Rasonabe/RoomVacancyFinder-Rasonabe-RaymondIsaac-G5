from django.urls import path
from . import views

urlpatterns = [
    path("", views.search, name="search"),
    path("reports/new/", views.report_create, name="report_create"),
    path("reports/<int:pk>/edit/", views.report_edit, name="report_edit"),
    path("reports/<int:pk>/delete/", views.report_delete, name="report_delete"),
]