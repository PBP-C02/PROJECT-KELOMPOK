from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('Auth_Profile.urls')),
    path('event/', include('Event.urls')),
    path('sport_partner/', include('Sport_Partner.urls')),
    path('court/', include('Court.urls')),
    path('coach/', include('Coach.urls')),
]
