import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils.formats import number_format
from Auth_Profile.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError


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


class Coach(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, related_name='coaches')
    peserta = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    isBooked = models.BooleanField(default=False)
    coach_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    title = models.CharField(max_length=255)
    image = models.ImageField(upload_to="coach/", null=True, blank=True)
    description = models.TextField()
    price = models.PositiveIntegerField(validators=[MinValueValidator(0)], default=1)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)

    location = models.CharField(max_length=255)
    address = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    date = models.DateField()
    startTime = models.TimeField()
    endTime = models.TimeField()

    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    instagram_link = models.URLField(blank=True, null=True,)
                                     

    def __str__(self):
        owner = getattr(self.user, "username", "anonymous")
        return f"{self.title} by {owner}"
    
    def clean(self):
        """Validasi custom untuk memastikan data valid"""
        super().clean()
        
        # Validasi: endTime harus lebih besar dari startTime
        if self.startTime and self.endTime and self.endTime <= self.startTime:
            raise ValidationError({
                'endTime': 'Waktu selesai harus lebih besar dari waktu mulai.'
            })
        
        # Validasi: date tidak boleh di masa lalu (untuk booking baru)
        if self.date and self.date < timezone.now().date():
            raise ValidationError({
                'date': 'Tanggal tidak boleh di masa lalu.'
            })
        
        if self.peserta and self.user and self.peserta == self.user:
            raise ValidationError({
                'peserta': 'Coach tidak bisa booking jadwal sendiri.'
            })
        
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def price_formatted(self):
        return f"Rp {number_format(self.price, decimal_pos=0, force_grouping=True)}"
    
    @property
    def is_past(self):
        """Cek apakah jadwal sudah lewat (berdasarkan date dan endTime)"""
        if not self.date:
            return False
        
        now = timezone.now()
        if self.date < now.date():
            return True
        
        if self.date == now.date() and self.endTime:
            return self.endTime < now.time()
        
        return False

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', 'price']),
            models.Index(fields=['location']),
            models.Index(fields=['created_at']),
        ]