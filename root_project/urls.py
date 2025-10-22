from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # COMMENT SEMUA APP YANG BELUM SIAP!
    # path('', include('Auth_Profile.urls')),
    # path('coach/', include('Coach.urls')),
    # path('court/', include('Court.urls')),
    # path('partner/', include('Sport_Partner.urls')),
    
    # Yang aktif cuma Event (kamu)
    path('event/', include('Event.urls')),
]

# Media files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)