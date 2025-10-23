from django.db import models
import uuid
from django.contrib.auth.models import AbstractUser

#INI GIMN YAHHH THEN: User(Models.model)
class User(AbstractUser):
    JENIS_KELAMIN = [
        ('L', 'Laki-laki'),
        ('P', 'Perempuan'),
    ]
    
    ROLE =[
        ('OWNER', 'OWNER'),
        ('BIASA', 'BIASA'),
        ('COACH', 'COACH')
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nama = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    role = models.CharField(choices=ROLE)
    kelamin = models.CharField(max_length=1, choices=JENIS_KELAMIN)
    tanggal_lahir = models.DateField()
    nomor_handphone = models.CharField(max_length=15)
    password = models.CharField(max_length=255)
    
    def __str__(self):
        return self.email