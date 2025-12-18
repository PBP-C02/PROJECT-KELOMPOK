from django import forms
from django.core.exceptions import ValidationError
from .models import Event, EventSchedule

CITY_CHOICES = [
    'Jakarta', 'Surabaya', 'Bandung', 'Medan', 'Bekasi',
    'Semarang', 'Tangerang', 'Depok', 'Palembang', 'Makassar',
    'Denpasar', 'Yogyakarta', 'Balikpapan', 'Malang', 'Batam',
]

_CITY_CANONICAL = {c.casefold(): c for c in CITY_CHOICES}

def canonical_city(value):
    if value is None:
        return None
    cleaned = " ".join(str(value).split()).strip()
    if not cleaned:
        return None
    return _CITY_CANONICAL.get(cleaned.casefold())

class EventForm(forms.ModelForm):
    city = forms.ChoiceField(
        choices=[(c, c) for c in CITY_CHOICES],
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = Event
        fields = [
            'name', 
            'sport_type', 
            'city', 
            'full_address', 
            'entry_price', 
            'activities', 
            'rating', 
            'description', 
            'google_maps_link', 
            'photo',  # ← FIXED: Changed from 'image' to 'photo'
            'category',
            'status'
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Event name'
            }),
            'sport_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'full_address': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': 'Complete address',
                'rows': 4
            }),
            'entry_price': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'Entry Price (IDR)',
                'step': '0.01'
            }),
            'activities': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Facilities (comma separated)'
            }),
            'rating': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': '0',
                'step': '0.01',
                'min': '0',
                'max': '5'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': 'Short description (optional)',
                'rows': 5
            }),
            'google_maps_link': forms.URLInput(attrs={
                'class': 'form-input',
                'placeholder': 'https://maps.google.com/?q=-6.2,106.8'
            }),
            'photo': forms.FileInput(attrs={  # ← FIXED: Changed from 'image' to 'photo'
                'class': 'form-file',
                'accept': 'image/*'
            }),
            'category': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Category (e.g., category 1)'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
        
        labels = {
            'name': 'Event Name',
            'sport_type': 'Sport Type',
            'city': 'City',
            'full_address': 'Full Address',
            'entry_price': 'Entry Price (IDR)',
            'activities': 'Activities (comma separated)',
            'rating': 'Rating (optional)',
            'description': 'Short description (optional)',
            'google_maps_link': 'Google Maps link',
            'photo': 'Event Photo (optional)',  # ← FIXED: Changed from 'image' to 'photo'
            'category': 'Category',
            'status': 'Status'
        }

    def clean_city(self):
        value = self.cleaned_data.get('city')
        city = canonical_city(value)
        if not city:
            raise ValidationError('Please select a valid city.')
        return city


class EventScheduleForm(forms.ModelForm):
    class Meta:
        model = EventSchedule
        fields = ['date', 'is_available']
        
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-input'
            }),
            'is_available': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            })
        }
