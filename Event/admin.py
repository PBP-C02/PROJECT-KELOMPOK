from django.contrib import admin
from django.utils.html import format_html
from .models import Event, EventRegistration, EventOrganizer, EventReview


@admin.register(EventOrganizer)
class EventOrganizerAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'user', 'is_superhost', 'total_events', 'average_rating', 'created_at')
    list_filter = ('is_superhost', 'created_at')
    search_fields = ('display_name', 'user__username', 'user__email')
    readonly_fields = ('total_events', 'created_at')
    
    fieldsets = (
        ('Info Dasar', {
            'fields': ('user', 'display_name', 'bio', 'profile_image')
        }),
        ('Status', {
            'fields': ('is_superhost', 'total_events')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        'name', 
        'category', 
        'level', 
        'date', 
        'time', 
        'city',
        'price_display',
        'participants_display',
        'average_rating',
        'is_active'
    )
    list_filter = ('category', 'level', 'city', 'is_active', 'date', 'organizer__is_superhost')
    search_fields = ('name', 'description', 'location_name', 'city')
    readonly_fields = ('created_at', 'updated_at', 'confirmed_participants_count', 'available_slots')
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Informasi Event', {
            'fields': ('name', 'description', 'image', 'organizer')
        }),
        ('Kategori & Level', {
            'fields': ('category', 'level')
        }),
        ('Tanggal & Waktu', {
            'fields': ('date', 'time', 'duration_hours')
        }),
        ('Lokasi', {
            'fields': ('location_name', 'location_address', 'city', 'latitude', 'longitude')
        }),
        ('Harga & Kapasitas', {
            'fields': ('price', 'max_participants', 'min_participants', 'confirmed_participants_count', 'available_slots')
        }),
        ('Detail Tambahan', {
            'fields': ('requirements', 'payment_info', 'refund_policy', 'instagram_link'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def price_display(self, obj):
        """Format tampilan harga"""
        return f"Rp {obj.price:,.0f}"
    price_display.short_description = 'Harga'
    
    def participants_display(self, obj):
        """Tampilkan peserta dengan warna"""
        confirmed = obj.confirmed_participants_count
        max_p = obj.max_participants
        percentage = (confirmed / max_p) * 100 if max_p > 0 else 0
        
        if percentage >= 90:
            color = 'red'
        elif percentage >= 70:
            color = 'orange'
        else:
            color = 'green'
            
        return format_html(
            '<span style="color: {};">{}/{}</span>',
            color, confirmed, max_p
        )
    participants_display.short_description = 'Peserta'


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = (
        'event',
        'user',
        'registration_date',
        'status',
        'payment_verified',
        'payment_proof_display'
    )
    list_filter = ('status', 'payment_verified', 'registration_date')
    search_fields = ('event__name', 'user__username', 'user__email')
    readonly_fields = ('registration_date',)
    
    fieldsets = (
        ('Info Pendaftaran', {
            'fields': ('event', 'user', 'status', 'notes')
        }),
        ('Info Pembayaran', {
            'fields': ('payment_proof', 'payment_verified', 'payment_date')
        }),
        ('Timestamps', {
            'fields': ('registration_date',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['confirm_registration', 'cancel_registration']
    
    def payment_proof_display(self, obj):
        """Tampilkan status bukti pembayaran"""
        if obj.payment_proof:
            return format_html(
                '<a href="{}" target="_blank">Lihat Bukti</a>',
                obj.payment_proof.url
            )
        return "Tidak ada bukti"
    payment_proof_display.short_description = 'Bukti Bayar'
    
    def confirm_registration(self, request, queryset):
        """Konfirmasi pendaftaran secara massal"""
        updated = queryset.update(status='confirmed')
        self.message_user(request, f'{updated} pendaftaran dikonfirmasi.')
    confirm_registration.short_description = 'Konfirmasi pendaftaran terpilih'
    
    def cancel_registration(self, request, queryset):
        """Batalkan pendaftaran secara massal"""
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} pendaftaran dibatalkan.')
    cancel_registration.short_description = 'Batalkan pendaftaran terpilih'


@admin.register(EventReview)
class EventReviewAdmin(admin.ModelAdmin):
    list_display = ('event', 'user', 'rating_display', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('event__name', 'user__username', 'comment')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Info Review', {
            'fields': ('event', 'user', 'rating', 'comment')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def rating_display(self, obj):
        """Tampilkan rating dengan bintang"""
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        return format_html('<span style="color: #FFD700;">{}</span>', stars)
    rating_display.short_description = 'Rating'