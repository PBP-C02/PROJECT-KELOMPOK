from django.db import models
from django.utils import timezone
from Auth_Profile.models import User
import uuid

class PartnerPost(models.Model):
    CATEGORY_CHOICES = [
        ('tennis', 'Tennis'),
        ('basketball', 'Basketball'),
        ('soccer', 'Soccer'),
        ('badminton', 'Badminton'),
        ('volleyball', 'Volleyball'),
        ('paddle', 'Paddle'),
        ('futsal', 'Futsal'),
        ('table_tennis', 'Table Tennis'),
        ('jogging', 'Jogging'),
    ]
    
    post_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='soccer')
    tanggal = models.DateField()
    jam_mulai = models.TimeField()
    jam_selesai = models.TimeField()
    lokasi = models.TextField()

    
    @property
    def total_participants(self):
        """Hitung participant secara dinamis dari PostParticipants"""
        return self.postparticipants_set.count()
    
    @property
    def participants_list(self):
        """Ambil list semua participant"""
        return self.postparticipants_set.select_related('participant').all()
    
    def add_participant(self, user):
        """Method untuk tambah participant"""
        # Cek apakah user sudah join
        if not self.postparticipants_set.filter(participant=user).exists():
            PostParticipants.objects.create(post_id=self, participant=user)
            return True
        return False
    
    def remove_participant(self, user):
        """Method untuk remove participant"""
        self.postparticipants_set.filter(participant=user).delete()
    
    def is_participant(self, user):
        """Cek apakah user sudah join"""
        return self.postparticipants_set.filter(participant=user).exists()
    
    def __str__(self):
        return self.title


class PostParticipants(models.Model):
    post_id = models.ForeignKey(PartnerPost, on_delete=models.CASCADE)
    participant = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ('post_id', 'participant')
    
    def __str__(self):
        return f"{self.participant.nama} joined {self.post_id.title}"
