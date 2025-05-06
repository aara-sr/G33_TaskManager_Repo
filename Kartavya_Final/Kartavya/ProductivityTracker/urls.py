from django.urls import path
from . import views

urlpatterns = [
    path('authorize_google/', views.authorize_google, name='authorize_google'),
    path('oauth2callback/', views.oauth2callback, name='oauth2callback'),
    path('calendar_sync/', views.calendar_sync, name='calendar_sync'),
    path('export/<int:task_id>/', views.export_task_to_calendar, name='export_task_to_calendar'),
]

