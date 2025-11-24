from django.urls import path
from . import views

app_name = 'event'

urlpatterns = [
    # Main pages
    path('', views.event_list, name='event_list'),
    path('<int:pk>/', views.event_detail, name='event_detail'),
    path('add/', views.add_event, name='add_event'),
    path('<int:pk>/edit/', views.edit_event, name='edit_event'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),  # NEW
    
    # AJAX endpoints for Search & Filter
    path('ajax/search/', views.ajax_search_events, name='ajax_search'),
    path('ajax/filter/', views.ajax_filter_sport, name='ajax_filter'),
    
    # AJAX endpoints for Add Event 
    path('ajax/validate/', views.ajax_validate_event_form, name='ajax_validate'),
    
    # AJAX endpoints for Edit Event 
    path('<int:pk>/ajax/delete/', views.ajax_delete_event, name='ajax_delete'),
    
    # AJAX endpoints for Event Detail & Join 
    path('<int:pk>/ajax/join/', views.ajax_join_event, name='ajax_join'),
    path('<int:pk>/ajax/cancel/', views.ajax_cancel_registration, name='ajax_cancel'),
    path('<int:pk>/ajax/toggle-availability/', views.ajax_toggle_availability, name='ajax_toggle_availability'),
    path('<int:pk>/ajax/schedules/', views.ajax_get_schedules, name='ajax_schedules'),
]