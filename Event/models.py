from django.db import models
from django.contrib.auth.models import User

class Event(models.Model):
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
    
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_events')
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)  # Pakai 'category' bukan 'sport_type'
    date = models.DateField()
    time = models.TimeField()
    location = models.CharField(max_length=255)
    max_participants = models.IntegerField()
    image = models.ImageField(upload_to='events/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    
    def available_slots(self):
        """Hitung slot yang masih tersedia"""
        registered = self.registrations.count()
        return self.max_participants - registered
    
    def is_full(self):
        """Cek apakah event sudah penuh"""
        return self.available_slots() <= 0

class EventRegistration(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_registrations')
    registered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('event', 'user')
    
    def __str__(self):
        return f"{self.user.username} - {self.event.title}"