from django import forms
from .models import Event, EventSchedule

class EventForm(forms.ModelForm):
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
            'city': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'City'
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