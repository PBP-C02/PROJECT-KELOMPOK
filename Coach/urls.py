from django.urls import path
from django.conf import settings
from Coach.views import *
from django.conf.urls.static import static

app_name = 'coach'

urlpatterns = [
    path('', show_main, name='show_main'),


    path('create-coach/', create_coach_page, name='create_coach_page'),  
    path('create-coach/submit/', add_coach, name='add_coach'),           


    path('edit-coach/<uuid:pk>/', edit_coach_page, name='edit_coach_page'),     
    path('update-coach/<uuid:pk>/', update_coach, name='update_coach'),          

    path('book-coach/<uuid:pk>/', book_coach, name='book_coach'), 
    path('cancel-booking/<uuid:pk>/', cancel_booking, name='cancel_booking'),  

    path('<uuid:pk>/', coach_detail, name='coach_detail'),       
    
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)