from django.urls import path
from django.conf import settings
from Coach.views import *
from django.conf.urls.static import static

app_name = 'coach'

urlpatterns = [
    path('', show_main, name='show_main'),

    # AJAX endpoints
    path('api/search/', ajax_search_coaches, name='ajax_search'),

    path('create-coach/', create_coach_page, name='create_coach_page'),  
    path('create-coach/submit/', add_coach, name='add_coach'),           

    path('edit-coach/<uuid:pk>/', edit_coach_page, name='edit_coach_page'),     
    path('update-coach/<uuid:pk>/', update_coach, name='update_coach'),          

    path('book-coach/<uuid:pk>/', book_coach, name='book_coach'), 
    path('cancel-booking/<uuid:pk>/', cancel_booking, name='cancel_booking'),  

    path('mark-available/<uuid:pk>/', mark_available, name='mark_available'),
    path('mark-unavailable/<uuid:pk>/', mark_unavailable, name='mark_unavailable'),
    path('delete-coach/<uuid:pk>/', delete_coach, name='delete_coach'),

    # Flutter endpoints
    path('create-flutter/', create_coach_flutter, name='create_coach_flutter'),
    path('update-flutter/<uuid:pk>/', update_coach_flutter, name='update_coach_flutter'),
    path('json/', show_json, name='show_json'),
    
    # Proxy image
    path('proxy-image/', proxy_image, name='proxy_image'),

    path('<uuid:pk>/', coach_detail, name='coach_detail'),
]
