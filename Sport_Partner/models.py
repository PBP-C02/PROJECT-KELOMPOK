from django.db import models
import uuid

# Create your models here.
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
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(choices=CATEGORY_CHOICES, default='sepakbola')
    time = models.TimeField()
    location = models.TextField()
    total_participants = models.PositiveIntegerField(default=0)

    @property
    def increment_total_participants(self):
        self.total_participants += 1
        self.save()

    