from django.urls import path, include
from Sport_Partner.views import *
urlpatterns = [
    path('', show_post, name='show-post'),
]
