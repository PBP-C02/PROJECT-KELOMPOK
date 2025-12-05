import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils.formats import number_format
from Auth_Profile.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from urllib.parse import quote


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

    location = models.CharField(max_length=400)
    address = models.TextField()
    mapsLink = models.URLField(max_length=400)
                    
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
        
        if self.startTime and self.endTime and self.endTime <= self.startTime:
            raise ValidationError({
                'endTime': 'Waktu selesai harus lebih besar dari waktu mulai.'
            })
        
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
        price_str = "{:,.0f}".format(self.price).replace(',', '.')
        return f"Rp {price_str}"
    
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

    def get_whatsapp_link(self):
        """Generate WhatsApp booking link"""
        if not self.user or not hasattr(self.user, 'nomor_handphone'):
            return None
        
        phone = self.user.nomor_handphone.strip().replace(' ', '').replace('-', '')
        
        # Format phone number to international format (62xxx)
        if phone.startswith('0'):
            phone = '62' + phone[1:]
        elif not phone.startswith('62'):
            phone = '62' + phone
        
        # Create booking message
        message = f"""Hello! I would like to book a coaching session:

*{self.title}*
 Date: {self.date.strftime('%A, %d %B %Y')}
 Time: {self.startTime.strftime('%H:%M')} - {self.endTime.strftime('%H:%M')}

Please confirm my booking. Thank you!"""    
        
        # URL encode message
        encoded_message = quote(message, safe='*\n')
        return f"https://wa.me/{phone}?text={encoded_message}"
    
    def get_formatted_phone(self):
        """Get formatted phone number"""
        if not self.user or not hasattr(self.user, 'nomor_handphone'):
            return None
        
        phone = self.user.nomor_handphone.strip()
        if len(phone) >= 10:
            return f"{phone[:4]}-{phone[4:8]}-{phone[8:]}"
        return phone
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', 'price']),
            models.Index(fields=['location']),
            models.Index(fields=['created_at']),
        ]