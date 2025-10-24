from django.db import models
from Auth_Profile.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

class Event(models.Model):
    """Model untuk event olahraga"""
    SPORT_CHOICES = [
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
    
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('unavailable', 'Unavailable'),
    ]
    
    # Basic Info
    name = models.CharField(max_length=200)
    sport_type = models.CharField(max_length=50, choices=SPORT_CHOICES)
    description = models.TextField(blank=True, null=True)
    #test
    # Location
    city = models.CharField(max_length=100)
    full_address = models.TextField()
    google_maps_link = models.URLField(blank=True, null=True)
    
    # Pricing & Details
    entry_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    activities = models.TextField(help_text="Comma separated facilities")
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00, validators=[MinValueValidator(0), MaxValueValidator(5)])
    
    # Event Photo
    photo = models.ImageField(upload_to='events/', blank=True, null=True)
    
    # Status & Metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    organizer = models.ForeignKey('Auth_Profile.User', on_delete=models.CASCADE, related_name='organized_events')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Categories (from image 4)
    category = models.CharField(max_length=100, default='category 1')
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.sport_type}"
    
    def get_activities_list(self):
        """Return activities as list"""
        if self.activities:
            return [activity.strip() for activity in self.activities.split(',')]
        return []
    
    def get_status_display_badge(self):
        """Return status with badge class"""
        return {
            'available': 'badge-available',
            'unavailable': 'badge-unavailable'
        }.get(self.status, 'badge-available')


class EventSchedule(models.Model):
    """Store available dates for events"""
    pk_event_sched = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='schedules')
    date = models.DateField()
    is_available = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['date']
        unique_together = ['event', 'date']
    
    def __str__(self):
        return f"{self.event.name} - {self.date}"


class EventRegistration(models.Model):
    """Join Event functionality"""
    pk_event_regis = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    user = models.ForeignKey('Auth_Profile.User', on_delete=models.CASCADE, related_name='event_registrations')
    schedule = models.ForeignKey(EventSchedule, on_delete=models.CASCADE, related_name='registrations')
    registered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-registered_at']
        unique_together = ['event', 'user', 'schedule']
    
    def __str__(self):
        return f"{self.user.username} - {self.event.name} ({self.schedule.date})"
