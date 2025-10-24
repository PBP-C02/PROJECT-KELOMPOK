from django.urls import path
from Sport_Partner.views import *

app_name = 'Sport_Partner'

urlpatterns = [
    path('', show_post, name='show_post'),
    path('create-post/', create_post, name='create_post'),
    path('post/<uuid:post_id>/', post_detail, name='post-detail'),
    path('post/<uuid:post_id>/participants/', get_participants_json, name='get_participants'),
    path('post/<uuid:post_id>/join/', join_post, name='join_post'),
    path('post/<uuid:post_id>/leave/', leave_post, name='leave_post'),
]
