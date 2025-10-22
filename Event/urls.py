from django.urls import path
from . import views

app_name = 'event'

urlpatterns = [
    path('', views.event_list, name='event_list'),
    path('<int:pk>/', views.event_detail, name='event_detail'),
    path('create/', views.create_event, name='create_event'),
    path('<int:pk>/edit/', views.edit_event, name='edit_event'),
    path('<int:pk>/delete/', views.delete_event, name='delete_event'),
    path('<int:pk>/register/', views.register_event, name='register_event'),
    path('<int:pk>/cancel/', views.cancel_registration, name='cancel_registration'),
]