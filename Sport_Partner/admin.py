from django.contrib import admin
from .models import PartnerPost, PostParticipants
# Register your models here.

admin.site.register(PostParticipants)
admin.site.register(PartnerPost)