from django.urls import path
from . import views

urlpatterns = [
    path('add/', views.add_task, name='add_task'),
    path('update/<int:task_id>/', views.update_task, name='update_task'),
    path('delete/<int:task_id>/', views.delete_task, name='delete_task'),
    path('complete/<int:task_id>/', views.complete_task, name='complete_task'),
    path('add_task/', views.add_task, name='add_task'),
    path('filter_tasks/', views.filter_tasks, name='filter_tasks'),
    path('upcoming/', views.upcoming_tasks, name='upcoming_tasks'),
    path('completed/', views.completed_tasks, name='completed_tasks'),
]