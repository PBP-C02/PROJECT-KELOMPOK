from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models import Avg


class EventOrganizer(models.Model):
    """Model untuk organizer/penyelenggara event"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='organizer_profile')
    display_name = models.CharField(max_length=200, verbose_name="Nama Tampilan")
    bio = models.TextField(blank=True, null=True)
    profile_image = models.ImageField(upload_to='organizers/', null=True, blank=True)
    is_superhost = models.BooleanField(default=False, verbose_name="Badge Superhost")
    total_events = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.display_name

    @property
    def average_rating(self):
        """Ambil rata-rata rating dari semua event"""
        avg = self.organized_events.aggregate(Avg('average_rating'))['average_rating__avg']
        return round(avg, 2) if avg else 0

    @property
    def total_reviews(self):
        """Total review dari semua event"""
        return sum(event.reviews.count() for event in self.organized_events.all())


class Event(models.Model):
    """Model untuk event olahraga"""
    CATEGORY_CHOICES = [
        ('tennis', 'Tennis'),
        ('basketball', 'Basketball'),
        ('soccer', 'Soccer'),
        ('badminton', 'Badminton'),
        ('volleyball', 'Volleyball'),
        ('paddle', 'Paddle'),
        ('futsal', 'Futsal'),
        ('table_tennis', 'Table Tennis'),
        ('swimming', 'Swimming'),
    ]

    LEVEL_CHOICES = [
        ('newbie', 'Newbie'),
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('pro', 'Pro'),
    ]

    name = models.CharField(max_length=200, verbose_name="Nama Event")
    description = models.TextField(verbose_name="Deskripsi")
    image = models.ImageField(upload_to='events/', null=True, blank=True)

    # Kategori & Level
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='badminton',
        verbose_name="Kategori Olahraga"
    )
    level = models.CharField(
        max_length=50,
        choices=LEVEL_CHOICES,
        default='beginner',
        verbose_name="Level"
    )

    # Tanggal & Waktu
    date = models.DateField(verbose_name="Tanggal Event")
    time = models.TimeField(verbose_name="Waktu Event")
    duration_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=2.0,
        verbose_name="Durasi (jam)"
    )

    # Lokasi
    location_name = models.CharField(max_length=200, verbose_name="Nama Tempat")
    location_address = models.TextField(verbose_name="Alamat Lengkap")
    city = models.CharField(max_length=100, default="Jakarta", verbose_name="Kota")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Harga & Peserta
    price = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="Harga per Orang")
    max_participants = models.IntegerField(validators=[MinValueValidator(1)], verbose_name="Maksimal Peserta")
    min_participants = models.IntegerField(validators=[MinValueValidator(1)], default=2, verbose_name="Minimal Peserta")
    
    # Penyelenggara
    organizer = models.ForeignKey(
        EventOrganizer, 
        on_delete=models.CASCADE, 
        related_name='organized_events',
        verbose_name="Penyelenggara"
    )
    
    # Detail Tambahan
    requirements = models.TextField(blank=True, null=True, help_text="Perlengkapan yang dibutuhkan, aturan, dll", verbose_name="Persyaratan")
    payment_info = models.TextField(blank=True, null=True, verbose_name="Info Pembayaran")
    refund_policy = models.CharField(max_length=50, default='no_refund', choices=[
        ('no_refund', 'Tidak Ada Refund'),
        ('partial', 'Refund Sebagian'),
        ('full', 'Refund Penuh'),
    ], verbose_name="Kebijakan Refund")
    
    # Media Sosial
    instagram_link = models.URLField(blank=True, null=True, verbose_name="Link Instagram")
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name="Aktif")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date', 'time']
        verbose_name = "Event"
        verbose_name_plural = "Events"

    def __str__(self):
        return f"{self.name} - {self.date}"

    @property
    def confirmed_participants_count(self):
        """Jumlah peserta yang sudah dikonfirmasi"""
        return self.registrations.filter(status='confirmed').count()

    @property
    def available_slots(self):
        """Slot yang masih tersedia"""
        return max(0, self.max_participants - self.confirmed_participants_count)

    @property
    def is_full(self):
        """Cek apakah event sudah penuh"""
        return self.available_slots == 0

    @property
    def is_past(self):
        """Cek apakah event sudah lewat"""
        from datetime import datetime
        event_datetime = datetime.combine(self.date, self.time)
        return timezone.now() > timezone.make_aware(event_datetime)

    @property
    def slots_remaining_text(self):
        """Text untuk menampilkan sisa slot"""
        slots = self.available_slots
        if slots == 0:
            return "Penuh!"
        elif slots <= 5:
            return f"Hanya tersisa {slots} slot!"
        return f"{slots} slot tersedia"

    @property
    def average_rating(self):
        """Rata-rata rating dari semua review"""
        avg = self.reviews.aggregate(Avg('rating'))['rating__avg']
        return round(avg, 2) if avg else 0


class EventRegistration(models.Model):
    """Model untuk pendaftaran event"""
    STATUS_CHOICES = [
        ('pending', 'Menunggu'),
        ('confirmed', 'Dikonfirmasi'),
        ('cancelled', 'Dibatalkan'),
        ('rejected', 'Ditolak'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations', verbose_name="Event")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_registrations', verbose_name="User")
    registration_date = models.DateTimeField(auto_now_add=True, verbose_name="Tanggal Daftar")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Status")
    notes = models.TextField(blank=True, null=True, verbose_name="Catatan")
    
    # Tracking Pembayaran
    payment_proof = models.ImageField(upload_to='payments/', null=True, blank=True, verbose_name="Bukti Pembayaran")
    payment_verified = models.BooleanField(default=False, verbose_name="Pembayaran Terverifikasi")
    payment_date = models.DateTimeField(null=True, blank=True, verbose_name="Tanggal Pembayaran")

    class Meta:
        ordering = ['-registration_date']
        unique_together = ['event', 'user']  # User hanya bisa daftar sekali per event
        verbose_name = "Pendaftaran Event"
        verbose_name_plural = "Pendaftaran Event"

    def __str__(self):
        return f"{self.user.username} - {self.event.name}"


class EventReview(models.Model):
    """Model untuk review event"""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='reviews', verbose_name="Event")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_reviews', verbose_name="User")
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Rating (1-5)"
    )
    comment = models.TextField(blank=True, null=True, verbose_name="Komentar")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['event', 'user']  # User hanya bisa review sekali per event
        verbose_name = "Review Event"
        verbose_name_plural = "Review Event"

    def __str__(self):
        return f"{self.user.username} - {self.event.name} ({self.rating}★)"