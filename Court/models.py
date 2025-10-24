# models.py
from django.db import models
from django.db.models import Q
from django.utils import timezone
from urllib.parse import quote

class Court(models.Model):
    SPORT_CHOICES = [
        ('tennis', 'Tennis'),
        ('basketball', 'Basketball'),
        ('soccer', 'Soccer'),
        ('badminton', 'Badminton'),
        ('volleyball', 'Volleyball'),
        ('paddle', 'Paddle'),
        ('futsal', 'Futsal'),
        ('table_tennis', 'Table Tennis'),
    ]
    
    name = models.CharField(max_length=200)
    sport_type = models.CharField(max_length=50, choices=SPORT_CHOICES)
    location = models.CharField(max_length=200)
    address = models.TextField()
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='Court/', blank=True, null=True)
    facilities = models.TextField()
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    
    # Coordinates for proximity features
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Owner contact for WhatsApp
    owner_name = models.CharField(max_length=100)
    owner_phone = models.CharField(max_length=20, help_text="Format: 628123456789 (without +)")
    created_by = models.ForeignKey(
        'Auth_Profile.User',
        on_delete=models.SET_NULL,
        related_name='courts',
        null=True,
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def get_facilities_list(self):
        """Return facilities as list"""
        return [f.strip() for f in self.facilities.split(',') if f.strip()]
    
    def is_available(self):
        """Backward-compatible availability check (any upcoming date)."""
        from datetime import date
        return not TimeSlot.objects.filter(
            court=self,
            date__gte=date.today(),
            is_available=False
        ).exists()

    def is_available_today(self):
        """Return availability status specifically for today's date."""
        today = timezone.localdate()
        slots = self.time_slots.filter(date=today)
        if not slots.exists():
            return True
        return not slots.filter(is_available=False).exists()
    
    def get_whatsapp_link(self, date=None, time=None):
        """Generate WhatsApp link for booking with URL-safe encoding."""
        base_url = f"https://wa.me/{self.owner_phone}"
        message = f"Hello, I would like to book the court *{self.name}*"
        if date and time:
            message += f" for date *{date}* at *{time}*"
        elif date:
            message += f" for date *{date}*"
        elif time:
            message += f" at *{time}*"

        encoded_message = quote(message, safe='*')
        return f"{base_url}?text={encoded_message}"
    
    class Meta:
        ordering = ['-rating', 'name']

class TimeSlot(models.Model):
    court = models.ForeignKey(Court, on_delete=models.CASCADE, related_name='time_slots')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['court', 'date', 'start_time']
        ordering = ['date', 'start_time']
    
    def __str__(self):
        return f"{self.court.name} - {self.date} {self.start_time}-{self.end_time}"
    
    def get_time_label(self):
        """Return formatted time label"""
        return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"
