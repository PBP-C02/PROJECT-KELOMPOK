from django.urls import path
from Auth_Profile.views import login_view, register_view, logout_view, homepage_view

app_name = 'Auth_Profile'

urlpatterns = [
    path('', homepage_view, name='homepage'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
]
