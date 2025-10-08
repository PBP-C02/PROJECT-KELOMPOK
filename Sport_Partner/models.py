from django.db import models
import uuid

# Create your models here.
class PartnerPost(models.Model):
    KATEGORI_OLAHRAGA = [
        ('sepakbola', 'Sepakbola'),
        ('basket', 'Basket'),
        ('tenis', 'Tenis'),
        ('padel', 'Padel'),
        ('bulu tangkis', 'Bulu Tangkis'),
        ('jogging', 'Jogging')
    ]

    post_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    judul = models.CharField(max_length=255)
    deskripsi = models.TextField()
    kategori = models.CharField(choices=KATEGORI_OLAHRAGA, default='sepakbola')
    jam = models.TimeField()
    lokasi = models.TextField()
    total_pendaftar = models.PositiveIntegerField(default=0)

    @property
    def increment_total_pendaftar(self):
        self.total_pendaftar += 1
        self.save()

    