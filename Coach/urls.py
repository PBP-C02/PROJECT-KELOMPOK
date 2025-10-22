from django.urls import path
from Coach.views import *

app_name = 'Coach'

urlpatterns = [
    path('', show_main, name='show_main'),
    path('coach/<str:id>/', show_coach, name='show_coach'),
    
    # path('create-product-ajax', add_product_entry_ajax, name='add_product_entry_ajax'),
    # path('update-product-ajax/<uuid:pk>/', update_product_entry_ajax, name='update_product_entry_ajax'),
    # path('delete-product-ajax/<uuid:pk>/', delete_product_entry_ajax, name='delete_product_entry_ajax'),
    
]