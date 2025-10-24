from django.db import models
import uuid

# Create your models here.
class User(models.Model):
    JENIS_KELAMIN = [
        ('L', 'Laki-laki'),
        ('P', 'Perempuan'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nama = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    kelamin = models.CharField(max_length=1, choices=JENIS_KELAMIN)
    tanggal_lahir = models.DateField()
    nomor_handphone = models.CharField(max_length=15)
    password = models.CharField(max_length=255)
    
    def __str__(self):
        return self.email