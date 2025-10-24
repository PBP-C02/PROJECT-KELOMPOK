from django.contrib import admin
from .models import Event, EventSchedule, EventRegistration

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'sport_type', 'city', 'entry_price', 'status', 'organizer', 'created_at')
    list_filter = ('sport_type', 'status', 'created_at')
    search_fields = ('name', 'city', 'description', 'organizer__username')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'sport_type', 'description')
        }),
        ('Location', {
            'fields': ('city', 'full_address', 'google_maps_link')
        }),
        ('Details', {
            'fields': ('entry_price', 'activities', 'rating', 'category')
        }),
        ('Media', {
            'fields': ('photo',)
        }),
        ('Status & Organizer', {
            'fields': ('status', 'organizer')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('organizer')


@admin.register(EventSchedule)
class EventScheduleAdmin(admin.ModelAdmin):
    list_display = ('event', 'date', 'is_available')
    list_filter = ('is_available', 'date')
    search_fields = ('event__name',)
    date_hierarchy = 'date'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('event')


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'schedule', 'registered_at')
    list_filter = ('registered_at',)
    search_fields = ('user__username', 'event__name')
    date_hierarchy = 'registered_at'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'event', 'schedule')