from django.urls import path
from . import views

app_name = 'Event'

urlpatterns = [
    # Listing event
    path('', views.event_list, name='event_list'),
    
    # Detail event
    path('<int:event_id>/', views.event_detail, name='event_detail'),

    path('create/', views.create_event, name='create_event'),
    
    # Pendaftaran
    path('<int:event_id>/register/', views.event_register, name='event_register'),
    path('registration/<int:registration_id>/cancel/', views.event_cancel_registration, name='event_cancel_registration'),
    
    # Review
    path('<int:event_id>/review/', views.event_add_review, name='event_add_review'),
    
    # Event user
    path('my-events/', views.my_events, name='my_events'),
]