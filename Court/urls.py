# urls.py (di app Court)
from django.urls import path
from . import views

app_name = 'Court'

urlpatterns = [
    # Main pages
    path('', views.show_main, name='show_main'),
    path('<int:court_id>/', views.court_detail, name='court_detail'),
    
    # API Endpoints untuk AJAX
    path('api/court/', views.get_all_Court, name='get_all_Court'),
    path('api/court/search/', views.api_search_court, name='api_search_court'),
    path('api/court/<int:court_id>/', views.get_court_detail, name='get_court_detail'),
    path('api/court/<int:court_id>/availability/', views.get_availability, name='get_availability'),
    path('api/court/whatsapp/', views.get_whatsapp_link, name='get_whatsapp_link'),
    
    path('add/', views.add_court, name='add_court'),
    path('api/court/add/', views.api_add_court, name='api_add_court'),
]