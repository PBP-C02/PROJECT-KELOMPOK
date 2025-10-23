from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('Auth_Profile.urls')),
    path('sport_partner/', include('Sport_Partner.urls')),
]
